import os
import json
import redis
from celery import Celery
from datetime import datetime
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon

from app.config import settings
from app.db.session import SessionLocal
from app.db.models import Hotspot, Alert
from app.services.spatial import compute_spatial_features
from app.services.inference import run_hotspot_inference
from app.services.plume import calculate_gaussian_plume_polygon
from app.services.firms_ingest import fetch_live_firms_data, generate_synthetic_firms_batch

celery_app = Celery("vulcangrid_tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "periodic-firms-ingest-every-10s": {
            "task": "app.workers.celery_app.periodic_firms_ingest",
            "schedule": 10.0,
        },
    },
)

def get_redis_client():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

@celery_app.task(name="app.workers.celery_app.process_hotspot_item")
def process_hotspot_item(item: dict) -> dict:
    """
    Celery pipeline per hotspot item:
    1. Feature engineering (FRP, brightness, confidence, spatial dist, H3 index, persistence)
    2. H3 context filter load-reduction check
    3. Tier 1 LightGBM -> Tier 2 PyTorch CNN
    4. SHAP feature explanation
    5. Save to PostGIS (Neon DB) & publish live alert to Redis channel
    """
    db = SessionLocal()
    try:
        acq_dt = datetime.fromisoformat(item["acq_datetime"].replace("Z", "+00:00"))
        lat = item["latitude"]
        lon = item["longitude"]
        frp = item["frp"]

        # 1. Compute Spatial & Context Features
        spatial_feats = compute_spatial_features(
            lat=lat, lon=lon, frp=frp, acq_datetime=acq_dt, db=db
        )

        h3_idx = spatial_feats["h3_index"]
        should_skip = spatial_feats["should_skip"]

        # Save Hotspot record
        point_geom = from_shape(Point(lon, lat), srid=4326)
        hotspot_rec = Hotspot(
            firms_id=item.get("firms_id"),
            latitude=lat,
            longitude=lon,
            location=point_geom,
            frp=frp,
            brightness=item["brightness"],
            bright_t31=item.get("bright_t31"),
            confidence=item.get("confidence"),
            acq_datetime=acq_dt,
            daynight=item.get("daynight", "D"),
            h3_index=h3_idx,
            skipped=should_skip
        )
        db.add(hotspot_rec)
        db.commit()
        db.refresh(hotspot_rec)

        # If H3 Context Filter skips this cell (e.g. low FRP far from any facility), mark & return
        if should_skip:
            db.close()
            return {"status": "skipped", "h3_index": h3_idx}

        # 2. Run AI Dual-Tier Inference & SHAP
        inf_res = run_hotspot_inference(
            frp=frp,
            brightness=item["brightness"],
            bright_t31=item.get("bright_t31", item["brightness"] - 30.0),
            confidence=item.get("confidence", 80.0),
            dist_to_industrial_km=spatial_feats["dist_to_industrial_km"],
            inside_facility=spatial_feats["inside_facility"],
            land_cover_class=spatial_feats["land_cover_class"],
            dist_to_solar_km=spatial_feats["dist_to_solar_km"],
            persistence_7d=spatial_feats["persistence_7d"],
            hour_of_day=spatial_feats["hour_of_day"]
        )

        pred_class = inf_res["predicted_class"]

        # 3. Calculate Gaussian Plume for Industrial Fire alerts
        plume_geom_shape = None
        wind_speed_ms = None
        wind_deg = None
        if pred_class == "industrial_fire":
            wind_speed_ms = 4.5
            wind_deg = 225.0
            plume_dict = calculate_gaussian_plume_polygon(lat, lon, wind_speed_ms, wind_deg)
            coords = plume_dict["coordinates"][0]
            plume_geom_shape = from_shape(Polygon(coords), srid=4326)

        # 4. Save Alert Record to Database
        alert_rec = Alert(
            hotspot_id=hotspot_rec.id,
            firms_id=item.get("firms_id"),
            latitude=lat,
            longitude=lon,
            location=point_geom,
            h3_index=h3_idx,
            frp=frp,
            brightness=item["brightness"],
            confidence=item.get("confidence", 80.0),
            acq_datetime=acq_dt,
            predicted_class=pred_class,
            class_probs=inf_res["class_probs"],
            tier_used=inf_res["tier_used"],
            overall_confidence=inf_res["overall_confidence"],
            shap_explanation=inf_res["shap_explanation"],
            feature_vector={
                "dist_to_industrial_km": spatial_feats["dist_to_industrial_km"],
                "inside_facility": spatial_feats["inside_facility"],
                "land_cover_class": spatial_feats["land_cover_class"],
                "dist_to_solar_km": spatial_feats["dist_to_solar_km"],
                "persistence_7d": spatial_feats["persistence_7d"],
                "hour_of_day": spatial_feats["hour_of_day"]
            },
            patch_image_base64=inf_res["patch_image_base64"],
            plume_geometry=plume_geom_shape,
            wind_speed_ms=wind_speed_ms,
            wind_deg=wind_deg,
            latency_ms=inf_res["latency_ms"]
        )
        db.add(alert_rec)
        db.commit()
        db.refresh(alert_rec)

        # 5. Broadcast to Redis Channel for Live WebSocket streaming (if Redis is available)
        try:
            r = get_redis_client()
            alert_payload = {
                "id": str(alert_rec.id),
                "firms_id": alert_rec.firms_id,
                "latitude": lat,
                "longitude": lon,
                "h3_index": h3_idx,
                "frp": frp,
                "brightness": item["brightness"],
                "confidence": item.get("confidence", 80.0),
                "acq_datetime": acq_dt.isoformat(),
                "predicted_class": pred_class,
                "class_probs": inf_res["class_probs"],
                "tier_used": inf_res["tier_used"],
                "overall_confidence": inf_res["overall_confidence"],
                "latency_ms": inf_res["latency_ms"],
                "created_at": alert_rec.created_at.isoformat()
            }
            r.publish("alerts_channel", json.dumps(alert_payload))
        except Exception as redis_err:
            # Non-fatal on serverless deployments without Redis instance
            pass

        db.close()
        return {"status": "alert_created", "alert_id": str(alert_rec.id), "class": pred_class}
    except Exception as e:
        db.rollback()
        db.close()
        print(f"[Celery Error] Processing hotspot item failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name="app.workers.celery_app.periodic_firms_ingest")
def periodic_firms_ingest():
    """
    Periodic task: Ingests FIRMS hotspots (Real FIRMS or Synthetic Stream) every 10s.
    """
    if settings.DEMO_MODE:
        batch = generate_synthetic_firms_batch(count=5)
    else:
        batch = fetch_live_firms_data()

    for item in batch:
        try:
            process_hotspot_item.delay(item)
        except Exception:
            process_hotspot_item(item)

    return {"ingested_count": len(batch)}
