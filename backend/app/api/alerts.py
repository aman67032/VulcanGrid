from typing import List, Optional
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import Alert, Hotspot, Facility
from app.workers.celery_app import process_hotspot_item
from app.services.plume import calculate_gaussian_plume_polygon

router = APIRouter(prefix="", tags=["Alerts & Analytics"])

class HotspotItemInput(BaseModel):
    firms_id: Optional[str] = None
    latitude: float
    longitude: float
    frp: float
    brightness: float
    bright_t31: Optional[float] = None
    confidence: Optional[float] = 80.0
    acq_datetime: str
    daynight: Optional[str] = "D"

class IngestBatchRequest(BaseModel):
    hotspots: List[HotspotItemInput]

@router.post("/ingest")
def ingest_hotspots(payload: IngestBatchRequest):
    """
    Accepts hotspot batches. Queues Celery or executes directly for Serverless environment (Vercel).
    """
    task_ids = []
    for item in payload.hotspots:
        item_dict = item.dict()
        try:
            # Try queuing via Celery
            res = process_hotspot_item.delay(item_dict)
            task_ids.append(res.id)
        except Exception:
            # Serverless fallback: process synchronously right inside request handler
            res_dict = process_hotspot_item(item_dict)
            task_ids.append(res_dict.get("alert_id", "sync-processed"))
    return {"status": "processed", "count": len(task_ids), "task_ids": task_ids}

@router.get("/alerts")
def get_alerts(
    predicted_class: Optional[str] = Query(None, description="Filter by class: controlled_flare, industrial_fire, forest_fire, false_alarm"),
    time_min: Optional[str] = Query(None, description="ISO datetime start filter"),
    time_max: Optional[str] = Query(None, description="ISO datetime end filter"),
    bbox: Optional[str] = Query(None, description="Bounding box min_lon,min_lat,max_lon,max_lat"),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieves classified alerts with spatial, time, and class filtering.
    """
    query = db.query(Alert)

    if predicted_class:
        query = query.filter(Alert.predicted_class == predicted_class)
    if time_min:
        try:
            dt_min = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
            query = query.filter(Alert.acq_datetime >= dt_min)
        except ValueError:
            pass
    if time_max:
        try:
            dt_max = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
            query = query.filter(Alert.acq_datetime <= dt_max)
        except ValueError:
            pass
    if bbox:
        try:
            parts = [float(p) for p in bbox.split(",")]
            if len(parts) == 4:
                min_lon, min_lat, max_lon, max_lat = parts
                bbox_wkt = f"ST_MakeEnvelope({min_lon}, {min_lat}, {max_lon}, {max_lat}, 4326)"
                query = query.filter(text(f"ST_Within(location, {bbox_wkt})"))
        except ValueError:
            pass

    alerts = query.order_by(Alert.acq_datetime.desc()).limit(limit).all()

    results = []
    for a in alerts:
        results.append({
            "id": str(a.id),
            "hotspot_id": str(a.hotspot_id) if a.hotspot_id else None,
            "firms_id": a.firms_id,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "h3_index": a.h3_index,
            "frp": a.frp,
            "brightness": a.brightness,
            "confidence": a.confidence,
            "acq_datetime": a.acq_datetime.isoformat(),
            "predicted_class": a.predicted_class,
            "class_probs": a.class_probs,
            "tier_used": a.tier_used,
            "overall_confidence": a.overall_confidence,
            "latency_ms": a.latency_ms,
            "created_at": a.created_at.isoformat()
        })
    return results

@router.get("/alerts/{alert_id}")
def get_alert_detail(alert_id: str, db: Session = Depends(get_db)):
    """
    Returns single alert detail including SHAP values and base64 false-colour composite patch image.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "id": str(alert.id),
        "hotspot_id": str(alert.hotspot_id) if alert.hotspot_id else None,
        "firms_id": alert.firms_id,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "h3_index": alert.h3_index,
        "frp": alert.frp,
        "brightness": alert.brightness,
        "confidence": alert.confidence,
        "acq_datetime": alert.acq_datetime.isoformat(),
        "predicted_class": alert.predicted_class,
        "class_probs": alert.class_probs,
        "tier_used": alert.tier_used,
        "overall_confidence": alert.overall_confidence,
        "shap_explanation": alert.shap_explanation,
        "feature_vector": alert.feature_vector,
        "patch_image_base64": alert.patch_image_base64,
        "wind_speed_ms": alert.wind_speed_ms,
        "wind_deg": alert.wind_deg,
        "latency_ms": alert.latency_ms,
        "created_at": alert.created_at.isoformat()
    }

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    Returns total alerts, per-class counts, average inference latency, and % H3 cells skipped.
    """
    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    total_hotspots = db.query(func.count(Hotspot.id)).scalar() or 0
    skipped_hotspots = db.query(func.count(Hotspot.id)).filter(Hotspot.skipped == True).scalar() or 0

    pct_skipped = (skipped_hotspots / total_hotspots * 100.0) if total_hotspots > 0 else 0.0

    class_counts_query = db.query(Alert.predicted_class, func.count(Alert.id)).group_by(Alert.predicted_class).all()
    class_counts = {cls: count for cls, count in class_counts_query}

    for expected_cls in ["controlled_flare", "industrial_fire", "forest_fire", "false_alarm"]:
        class_counts.setdefault(expected_cls, 0)

    avg_latency = db.query(func.avg(Alert.latency_ms)).scalar() or 0.0

    return {
        "total_alerts": total_alerts,
        "total_hotspots_evaluated": total_hotspots,
        "skipped_hotspots": skipped_hotspots,
        "pct_cells_skipped": round(pct_skipped, 2),
        "avg_latency_ms": round(float(avg_latency), 2),
        "class_counts": class_counts
    }

@router.get("/plume/{alert_id}")
def get_plume_polygon(alert_id: str, db: Session = Depends(get_db)):
    """
    Returns Gaussian plume dispersion GeoJSON polygon for an industrial fire alert.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    plume_geojson = calculate_gaussian_plume_polygon(
        lat=alert.latitude,
        lon=alert.longitude,
        wind_speed_ms=alert.wind_speed_ms or 4.5,
        wind_deg=alert.wind_deg or 225.0
    )

    return {
        "type": "Feature",
        "geometry": plume_geojson,
        "properties": {
            "alert_id": str(alert.id),
            "class": alert.predicted_class,
            "wind_speed_ms": alert.wind_speed_ms or 4.5,
            "wind_deg": alert.wind_deg or 225.0
        }
    }

@router.get("/facilities")
def get_facilities(db: Session = Depends(get_db)):
    """
    Returns industrial & solar facility boundary polygons in GeoJSON format for the map overlay.
    """
    query = text("SELECT id, name, facility_type, ST_AsGeoJSON(geometry) as geojson FROM facilities;")
    rows = db.execute(query).fetchall()

    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(r[3]),
            "properties": {
                "id": str(r[0]),
                "name": r[1],
                "facility_type": r[2]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
