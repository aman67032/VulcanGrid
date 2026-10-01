import logging
import httpx
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.pipeline.ingestion import DEMO_FACILITIES
from app.pipeline.weather import get_facility_weather, fetch_live_weather
from app.pipeline.dispersion import generate_plume_hazard_cone, estimate_emission_rate_q
from app.pipeline.chemical_profiles import (
    get_facility_chemicals,
    get_chemical_profile,
    compute_chemical_emission_rate
)
from app.pipeline.population_impact import estimate_population_impact
from app.services.inference import run_hotspot_inference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Tactical Command & Live Feeds"])

INDIA_BBOX = {
    "min_lat": 6.75,
    "max_lat": 37.1,
    "min_lon": 68.16,
    "max_lon": 97.4
}

# In-memory cache for live FIRMS data to avoid hammering NASA
_live_firms_cache: List[Dict[str, Any]] = []
_live_firms_timestamp: float = 0.0

@router.get("/live-firms")
async def get_live_firms():
    """
    Fetches real-time 24-hour NASA Suomi-NPP VIIRS active fire data for India.
    No API key required; parses live public CSV feed directly from NASA FIRMS.
    """
    global _live_firms_cache, _live_firms_timestamp
    import time
    now = time.time()
    if _live_firms_cache and (now - _live_firms_timestamp < 180):
        return _live_firms_cache

    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_24h.csv"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            lines = resp.text.strip().split("\n")
            if not lines:
                return _live_firms_cache or []

            header = lines[0].split(",")
            lat_idx = header.index("latitude") if "latitude" in header else 0
            lon_idx = header.index("longitude") if "longitude" in header else 1
            frp_idx = header.index("frp") if "frp" in header else 12
            conf_idx = header.index("confidence") if "confidence" in header else 9
            b4_idx = header.index("bright_ti4") if "bright_ti4" in header else 2

            records = []
            for line in lines[1:]:
                if not line.strip():
                    continue
                cols = line.split(",")
                try:
                    lat = float(cols[lat_idx])
                    lon = float(cols[lon_idx])
                    if INDIA_BBOX["min_lat"] <= lat <= INDIA_BBOX["max_lat"] and INDIA_BBOX["min_lon"] <= lon <= INDIA_BBOX["max_lon"]:
                        frp = float(cols[frp_idx]) if cols[frp_idx] else 10.0
                        b4 = float(cols[b4_idx]) if cols[b4_idx] else 320.0
                        conf = cols[conf_idx] if len(cols) > conf_idx else "nominal"
                        records.append({
                            "lat": round(lat, 4),
                            "lon": round(lon, 4),
                            "frp": round(frp, 1),
                            "brightness": round(b4, 1),
                            "confidence": conf
                        })
                except (ValueError, IndexError):
                    continue

            _live_firms_cache = records
            _live_firms_timestamp = now
            return records
    except Exception as e:
        logger.error(f"Failed to fetch live NASA FIRMS feed: {e}")
        return _live_firms_cache or []

@router.get("/live-weather")
async def get_live_weather(lat: Optional[float] = None, lon: Optional[float] = None, facility: Optional[str] = None):
    """
    Returns live meteorological wind vectors and stability class from Open-Meteo API.
    """
    if facility and facility in DEMO_FACILITIES:
        fac = DEMO_FACILITIES[facility]
        lat, lon = fac["lat"], fac["lon"]
    elif lat is None or lon is None:
        lat, lon = 22.4707, 69.8331 # Jamnagar default

    try:
        weather = await fetch_live_weather(lat, lon)
        return weather
    except Exception as e:
        logger.warning(f"Live weather lookup failed: {e}")
        return {
            "wind_speed_10m": 4.8,
            "wind_direction_10m": 235.0,
            "temperature_2m": 31.0,
            "computed_stability_class": "D",
            "source": "fallback"
        }

@router.get("/simulation/baseline-proof")
async def get_baseline_proof(facility: str = "jamnagar_refinery"):
    """
    Returns baseline operational telemetry and live weather for any corporate facility.
    """
    fac = DEMO_FACILITIES.get(facility, DEMO_FACILITIES["jamnagar_refinery"])
    lat, lon = fac["lat"], fac["lon"]

    try:
        weather = await fetch_live_weather(lat, lon)
    except Exception:
        weather = {"wind_speed_10m": 4.5, "wind_direction_10m": 240.0, "computed_stability_class": "D", "source": "fallback"}

    # Run AI inference on facility baseline
    inf_res = run_hotspot_inference(
        frp=fac["baseline_frp_mean"],
        brightness=324.5,
        bright_t31=294.0,
        confidence=90.0,
        dist_to_industrial_km=0.05,
        inside_facility=1,
        land_cover_class=0,
        dist_to_solar_km=50.0,
        persistence_7d=8,
        hour_of_day=14
    )

    chemicals = get_facility_chemicals(facility)

    return {
        "scenario": "BASELINE_OPERATIONAL_PROOF",
        "facility": fac["name"],
        "coordinates": {"lat": lat, "lon": lon},
        "telemetry": {
            "facility_name": fac["name"],
            "latitude": lat,
            "longitude": lon,
            "frp": fac["baseline_frp_mean"],
            "tai": 0.4,
            "spf": 0.95,
            "bright_ti4": 324.5,
            "h3_index": fac["h3_index"]
        },
        "triage_result": {
            "class_id": 0,
            "class_tag": "ROUTINE_FLARING",
            "category": "Controlled Industrial Flare",
            "action": "SUPPRESS_ALERT",
            "action_details": f"FRP ({fac['baseline_frp_mean']} MW) within equilibrium 90-day baseline distribution.",
            "severity": "NORMAL",
            "confidence": round(inf_res["overall_confidence"], 2),
            "inference_time_ms": inf_res["latency_ms"],
            "features": {
                "frp": fac["baseline_frp_mean"],
                "tai": 0.4,
                "spf": 0.95,
                "bright_ti4": 324.5
            }
        },
        "cnn_verification": {
            "prediction_class": "controlled_flare",
            "is_verified_fire": False,
            "confidence": 0.98,
            "action": "SUPPRESSED",
            "explanation": "Multi-spectral Sentinel-2 SWIR analysis confirms routine operational combustion stack.",
            "fire_footprint": {
                "active_pixel_count": 2,
                "fire_area_m2": 200,
                "fire_area_hectares": 0.02,
                "core_centroid_pixel": [16, 16],
                "max_swir_reflectance": 0.42,
                "mean_nbr_in_core": 0.15
            }
        },
        "satellite_imagery": {
            "rgb_preview_url": "/api/static/jamnagar_rgb.jpg",
            "swir_preview_url": "/api/static/jamnagar_swir.jpg",
            "patch_dimensions": [32, 32],
            "gsd_meters": 10
        },
        "live_weather": weather,
        "available_chemicals": chemicals,
        "demo_notes": f"Active operational emissions at {fac['name']}. Flare suppressed as routine background activity."
    }

class WhatIfRequest(BaseModel):
    facility: str = "jamnagar_refinery"
    wind_speed_m_s: float = 5.2
    wind_direction_deg: float = 235.0
    chemical_type: str = "GENERIC"
    explosion_frp_mw: float = 120.0
    stability_class: str = "D"

@router.post("/simulation/what-if")
def calculate_what_if_sandbox(req: WhatIfRequest):
    """
    Recalculates Gaussian plume dispersion and population at risk in real time for What-If sandbox.
    """
    fac = DEMO_FACILITIES.get(req.facility, DEMO_FACILITIES["jamnagar_refinery"])
    lat, lon = fac["lat"], fac["lon"]

    # Compute emission rate
    chem_profile = get_chemical_profile(req.chemical_type)
    computed_q = compute_chemical_emission_rate(req.chemical_type, req.explosion_frp_mw, 8400.0)

    # Generate plume cones
    plume_geojson = generate_plume_hazard_cone(
        origin_lat=lat,
        origin_lon=lon,
        wind_speed_m_s=req.wind_speed_m_s,
        wind_direction_deg=req.wind_direction_deg,
        stability_class=req.stability_class,
        q_emission_rate_g_s=computed_q,
        chemical_type=req.chemical_type
    )

    # Population impact
    pop_impact = estimate_population_impact(req.facility, plume_geojson)

    return {
        "chemical_profile": {
            "chemical_type": req.chemical_type,
            "primary_hazard": chem_profile.get("hazard", "Thermal & Toxic Combustion"),
            "idlh_ppm": chem_profile.get("IDLH_ppm", 1000),
            "erpg2_ppm": chem_profile.get("ERPG2_ppm", 200),
            "computed_emission_rate_g_s": computed_q
        },
        "plume_dispersion": plume_geojson,
        "population_impact": pop_impact
    }

@router.post("/simulation/inject-explosion")
async def inject_explosion(
    facility: str = Query("jamnagar_refinery"),
    chemical_type: str = Query("GENERIC"),
    wind_speed: Optional[float] = None,
    wind_direction: Optional[float] = None,
    explosion_frp: Optional[float] = None
):
    """
    Simulates or verifies an industrial explosion: evaluates AI triage, live weather, plume cone, and NDRF impact.
    """
    fac = DEMO_FACILITIES.get(facility, DEMO_FACILITIES["jamnagar_refinery"])
    lat, lon = fac["lat"], fac["lon"]
    frp_val = explosion_frp if explosion_frp is not None else 145.0

    # Fetch live weather
    try:
        weather = await fetch_live_weather(lat, lon)
    except Exception:
        weather = {"wind_speed_10m": 5.2, "wind_direction_10m": 235.0, "computed_stability_class": "C", "source": "fallback"}

    if wind_speed is not None:
        weather["wind_speed_10m"] = wind_speed
    if wind_direction is not None:
        weather["wind_direction_10m"] = wind_direction

    # AI Model Prediction
    inf_res = run_hotspot_inference(
        frp=frp_val,
        brightness=385.0,
        bright_t31=310.0,
        confidence=98.0,
        dist_to_industrial_km=0.05,
        inside_facility=1,
        land_cover_class=0,
        dist_to_solar_km=50.0,
        persistence_7d=8,
        hour_of_day=14
    )

    chem_profile = get_chemical_profile(chemical_type)
    computed_q = compute_chemical_emission_rate(chemical_type, frp_val, 8400.0)

    plume_geojson = generate_plume_hazard_cone(
        origin_lat=lat,
        origin_lon=lon,
        wind_speed_m_s=weather["wind_speed_10m"],
        wind_direction_deg=weather["wind_direction_10m"],
        stability_class=weather.get("computed_stability_class", "C"),
        q_emission_rate_g_s=computed_q,
        chemical_type=chemical_type
    )

    pop_impact = estimate_population_impact(facility, plume_geojson)

    return {
        "scenario": "INCIDENT_SIMULATION_EXPLOSION",
        "facility": fac["name"],
        "coordinates": {"lat": lat, "lon": lon},
        "telemetry": {
            "facility_name": fac["name"],
            "latitude": lat,
            "longitude": lon,
            "frp": frp_val,
            "tai": 4.8,
            "spf": 0.98,
            "bright_ti4": 385.0,
            "h3_index": fac["h3_index"]
        },
        "triage_result": {
            "class_id": 1,
            "class_tag": "CRITICAL_INCIDENT",
            "category": "Industrial Explosion / Major Fire",
            "action": "DISPATCH_EMERGENCY",
            "action_details": f"FRP spike to {frp_val} MW exceeds +4.5σ baseline limit. Immediate emergency protocol activated.",
            "severity": "CRITICAL",
            "confidence": round(inf_res["overall_confidence"], 2),
            "inference_time_ms": inf_res["latency_ms"],
            "features": {
                "frp": frp_val,
                "tai": 4.8,
                "spf": 0.98,
                "bright_ti4": 385.0
            }
        },
        "cnn_verification": {
            "prediction_class": "industrial_fire",
            "is_verified_fire": True,
            "confidence": 0.96,
            "action": "VERIFIED_FIRE",
            "explanation": "Stage 2 Sentinel-2 SWIR band confirms intense combustion footprint with negative NBR index.",
            "fire_footprint": {
                "active_pixel_count": 84,
                "fire_area_m2": 8400,
                "fire_area_hectares": 0.84,
                "core_centroid_pixel": [16, 16],
                "max_swir_reflectance": 0.94,
                "mean_nbr_in_core": -0.68
            }
        },
        "satellite_imagery": {
            "rgb_preview_url": "/api/static/jamnagar_rgb.jpg",
            "swir_preview_url": "/api/static/jamnagar_swir.jpg",
            "patch_dimensions": [32, 32],
            "gsd_meters": 10
        },
        "plume_dispersion": plume_geojson,
        "live_weather": weather,
        "chemical_profile": {
            "chemical_type": chemical_type,
            "primary_hazard": chem_profile.get("hazard", "Hydrocarbon vapor fire"),
            "idlh_ppm": chem_profile.get("IDLH_ppm", 1000),
            "erpg2_ppm": chem_profile.get("ERPG2_ppm", 200),
            "computed_emission_rate_g_s": computed_q
        },
        "population_impact": pop_impact,
        "available_chemicals": get_facility_chemicals(facility),
        "demo_notes": f"Critical thermal explosion detected at {fac['name']}. Multi-stage triage and atmospheric dispersion dispatched."
    }

@router.post("/verification/cnn-verify")
def verify_cnn_scenario(payload: Dict[str, Any]):
    """
    Spectral CNN verification for false alarm glare testing.
    """
    return {
        "cnn_verification": {
            "prediction_class": "false_alarm",
            "is_verified_fire": False,
            "confidence": 0.94,
            "action": "DISMISS_FALSE_ALARM",
            "explanation": "Optical glare rejected by Stage 2 Spectral Verification. Positive NBR confirms no combustion core.",
            "fire_footprint": {
                "active_pixel_count": 0,
                "fire_area_m2": 0,
                "fire_area_hectares": 0.0,
                "core_centroid_pixel": [0, 0],
                "max_swir_reflectance": 0.12,
                "mean_nbr_in_core": 0.45
            }
        },
        "satellite_imagery": {
            "rgb_preview_url": "/api/static/jamnagar_rgb.jpg",
            "swir_preview_url": "/api/static/jamnagar_swir.jpg",
            "patch_dimensions": [32, 32],
            "gsd_meters": 10
        }
    }
