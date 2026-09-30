import random
import requests
import datetime
from typing import List, Dict, Any
from app.config import settings

# Key industrial and forest hotspot centers across India
HOTSPOT_ANCHORS = [
    # Jamnagar Refinery Complex (Industrial Flare / Fire)
    {"lat": 22.3500, "lon": 69.8500, "name": "Jamnagar", "type": "industrial"},
    # Vadodara Petrochemical Industrial Zone
    {"lat": 22.3800, "lon": 73.1500, "name": "Vadodara", "type": "industrial"},
    # Haldia Petrochemicals Hub
    {"lat": 22.0300, "lon": 88.0800, "name": "Haldia", "type": "industrial"},
    # Paradip Refinery & Port Estate
    {"lat": 20.2700, "lon": 86.6700, "name": "Paradip", "type": "industrial"},
    # Bhadla Solar Park (False alarm glare)
    {"lat": 27.5300, "lon": 71.9100, "name": "Bhadla", "type": "solar"},
    # Uttarakhand Dense Forest Region (Wildfire)
    {"lat": 30.1200, "lon": 79.2500, "name": "Uttarakhand Forest", "type": "forest"},
    # Similipal Forest Odisha (Wildfire)
    {"lat": 21.9000, "lon": 86.3000, "name": "Similipal Forest", "type": "forest"}
]

def fetch_live_firms_data() -> List[Dict[str, Any]]:
    """
    Fetches real active fire data from NASA FIRMS VIIRS_SNPP_NRT API for India region.
    """
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{settings.FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/68,8,97,37/1"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "latitude" in response.text:
            lines = response.text.strip().split("\n")
            header = lines[0].split(",")
            hotspots = []
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) >= len(header):
                    row = dict(zip(header, parts))
                    try:
                        hotspots.append({
                            "firms_id": f"FIRMS-{row.get('latitude')}-{row.get('longitude')}-{row.get('acq_date')}",
                            "latitude": float(row["latitude"]),
                            "longitude": float(row["longitude"]),
                            "frp": float(row["frp"]) if row.get("frp") else 15.0,
                            "brightness": float(row["bright_ti4"]) if row.get("bright_ti4") else 330.0,
                            "bright_t31": float(row["bright_ti5"]) if row.get("bright_ti5") else 295.0,
                            "confidence": float(row["confidence"]) if row.get("confidence") not in [None, 'n', 'l', 'h'] else (90.0 if row.get("confidence") == 'h' else 50.0),
                            "acq_datetime": f"{row['acq_date']}T{row['acq_time'][:2]}:{row['acq_time'][2:]}:00Z" if len(row.get('acq_time', '')) >= 4 else datetime.datetime.utcnow().isoformat(),
                            "daynight": row.get("daynight", "D")
                        })
                    except (ValueError, KeyError):
                        continue
            if hotspots:
                return hotspots
    except Exception as e:
        print(f"[FIRMS API Error] Failed fetching live FIRMS data: {e}. Falling back to synthetic generator.")

    return generate_synthetic_firms_batch(count=15)

def generate_synthetic_firms_batch(count: int = 15) -> List[Dict[str, Any]]:
    """
    Generates synthetic FIRMS hotspot detections around Indian industrial hubs & forest zones.
    """
    hotspots = []
    now = datetime.datetime.utcnow()

    for i in range(count):
        anchor = random.choice(HOTSPOT_ANCHORS)

        # Jitter coordinates within ~2-5 km of anchor
        lat = anchor["lat"] + random.uniform(-0.04, 0.04)
        lon = anchor["lon"] + random.uniform(-0.04, 0.04)

        target_type = anchor["type"]
        if target_type == "industrial":
            if random.random() < 0.65: # Flare
                frp = random.uniform(30.0, 90.0)
                brightness = random.uniform(330.0, 360.0)
                confidence = random.uniform(85.0, 100.0)
            else: # Fire
                frp = random.uniform(70.0, 180.0)
                brightness = random.uniform(350.0, 385.0)
                confidence = random.uniform(90.0, 100.0)
        elif target_type == "solar": # False alarm glare
            frp = random.uniform(1.5, 6.0)
            brightness = random.uniform(315.0, 335.0)
            confidence = random.uniform(40.0, 75.0)
        else: # Forest
            frp = random.uniform(20.0, 110.0)
            brightness = random.uniform(325.0, 355.0)
            confidence = random.uniform(70.0, 95.0)

        hotspots.append({
            "firms_id": f"SYN-{now.strftime('%Y%m%d%H%M%S')}-{i:03d}",
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "frp": round(frp, 2),
            "brightness": round(brightness, 2),
            "bright_t31": round(brightness - random.uniform(30.0, 45.0), 2),
            "confidence": round(confidence, 1),
            "acq_datetime": now.isoformat() + "Z",
            "daynight": "D" if 6 <= now.hour <= 18 else "N"
        })

    return hotspots
