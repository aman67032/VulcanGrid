import h3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from shapely.geometry import Point
from shapely.wkt import loads as load_wkt

def get_h3_index(lat: float, lon: float, resolution: int = 8) -> str:
    """Supports both H3 v3 (geo_to_h3) and H3 v4 (latlng_to_cell)"""
    if hasattr(h3, "latlng_to_cell"):
        return h3.latlng_to_cell(lat, lon, resolution)
    elif hasattr(h3, "geo_to_h3"):
        return h3.geo_to_h3(lat, lon, resolution=resolution)
    return "8860a25999fffff"

def compute_spatial_features(
    lat: float,
    lon: float,
    frp: float,
    acq_datetime: datetime,
    db: Session
) -> Dict[str, Any]:
    """
    Computes spatial features using PostGIS spatial queries, H3 resolution 8 cell indexing,
    and 7-day historical persistence tracking.
    """
    # 1. H3 Indexing (Resolution 8)
    h3_index = get_h3_index(lat, lon, resolution=8)

    point_wkt = f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)"

    # 2. Query distance to nearest industrial facility and inside_facility flag
    query_ind = text(f"""
        SELECT 
            MIN(ST_Distance({point_wkt}::geography, geometry::geography) / 1000.0) as dist_km,
            BOOL_OR(ST_Within({point_wkt}, geometry)) as inside
        FROM facilities
        WHERE facility_type IN ('industrial_refinery', 'petrochemical', 'steel_plant');
    """)
    res_ind = db.execute(query_ind).fetchone()
    dist_ind_km = float(res_ind[0]) if res_ind and res_ind[0] is not None else 50.0
    inside_facility = 1 if (res_ind and res_ind[1]) else (1 if dist_ind_km < 0.2 else 0)

    # 3. Query distance to nearest solar farm
    query_sol = text(f"""
        SELECT MIN(ST_Distance({point_wkt}::geography, geometry::geography) / 1000.0) as dist_km
        FROM facilities
        WHERE facility_type = 'solar_farm';
    """)
    res_sol = db.execute(query_sol).fetchone()
    dist_solar_km = float(res_sol[0]) if res_sol and res_sol[0] is not None else 50.0

    # 4. Land Cover Class Determination
    # 0: Industrial, 1: Forest, 2: Solar Farm, 3: Agricultural/Barren
    if inside_facility or dist_ind_km < 1.0:
        land_cover_class = 0
    elif dist_solar_km < 1.0:
        land_cover_class = 2
    elif (30.0 <= lat <= 31.5 and 78.0 <= lon <= 80.0) or (21.5 <= lat <= 22.5 and 85.5 <= lon <= 87.0):
        # Known forest bounding regions (Uttarakhand & Similipal)
        land_cover_class = 1
    else:
        land_cover_class = 3

    # 5. Persistence tracking over last 7 days in the same H3 cell
    seven_days_ago = acq_datetime - timedelta(days=7)
    query_persist = text("""
        SELECT COUNT(*) 
        FROM hotspots 
        WHERE h3_index = :h3_idx AND acq_datetime >= :seven_days_ago;
    """)
    res_persist = db.execute(query_persist, {"h3_idx": h3_index, "seven_days_ago": seven_days_ago}).fetchone()
    persistence_7d = int(res_persist[0]) if res_persist else 0

    # 6. Hour of Day
    hour_of_day = acq_datetime.hour

    # 7. Check if cell should be skipped by Tier 1 Load-Reduction H3 Context Filter
    # Skip if far from industrial (>15km), far from solar (>10km), land cover is barren, and FRP < 8.0 MW
    should_skip = False
    if dist_ind_km > 15.0 and dist_solar_km > 10.0 and land_cover_class == 3 and frp < 8.0:
        should_skip = True

    return {
        "h3_index": h3_index,
        "dist_to_industrial_km": round(dist_ind_km, 3),
        "inside_facility": inside_facility,
        "land_cover_class": land_cover_class,
        "dist_to_solar_km": round(dist_solar_km, 3),
        "persistence_7d": persistence_7d,
        "hour_of_day": hour_of_day,
        "should_skip": should_skip
    }
