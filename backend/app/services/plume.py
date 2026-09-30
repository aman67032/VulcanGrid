import math
import requests
import numpy as np
from typing import Dict, Any, List, Tuple

def fetch_live_wind_vector(lat: float, lon: float) -> Tuple[float, float]:
    """
    Fetches real-time 10m wind speed (m/s) and wind direction (degrees) from Open-Meteo API.
    Falls back to (4.5 m/s, 225.0 deg) if API is unavailable or offline.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}&current=wind_speed_10m,wind_direction_10m"
    try:
        response = requests.get(url, timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            speed = float(current.get("wind_speed_10m", 4.5))
            # Open-Meteo wind_speed_10m is in km/h; convert to m/s
            speed_ms = speed / 3.6 if speed > 15.0 else speed
            deg = float(current.get("wind_direction_10m", 225.0))
            return round(speed_ms, 2), round(deg, 1)
    except Exception as e:
        print(f"[Open-Meteo Warning] Live wind lookup failed: {e}. Using default vector.")

    return 4.5, 225.0

def calculate_gaussian_plume_polygon(
    lat: float,
    lon: float,
    wind_speed_ms: float = 4.5,
    wind_deg: float = 225.0,  # Direction wind is coming FROM (225 = SW, so plume blows NE)
    plume_length_km: float = 5.0,
    max_width_km: float = 1.2,
    num_points: int = 20,
    use_live_wind: bool = False
) -> Dict[str, Any]:
    """
    Computes a 2D Gaussian plume dispersion polygon emanating from a hotspot (lat, lon).
    Returns GeoJSON Geometry Polygon dict.
    """
    if use_live_wind:
        wind_speed_ms, wind_deg = fetch_live_wind_vector(lat, lon)

    # Convert wind direction from "direction FROM" to "direction TOWARDS" in radians
    # 0 deg = North, 90 deg = East
    angle_rad = math.radians((wind_deg + 180) % 360)

    # Conversion factors for lat/lon (approx at India latitudes ~20-25N)
    # 1 deg lat ~= 111 km, 1 deg lon ~= 111 * cos(lat) km
    lat_km = 111.0
    lon_km = 111.0 * math.cos(math.radians(lat))

    # Centerline downwind points
    downwind_distances = np.linspace(0, plume_length_km, num_points)

    right_edge = []
    left_edge = []

    for s in downwind_distances:
        if s == 0:
            sigma_y = 0.0
        else:
            # Pasquill-Gifford Stability Class D/C plume dispersion parameterization: sigma_y = a * s^b
            sigma_y = min(0.12 * (s ** 0.9), max_width_km / 2.0)

        # Centerline position (x = East, y = North in km)
        x_center = s * math.sin(angle_rad)
        y_center = s * math.cos(angle_rad)

        # Perpendicular unit vector (crosswind direction)
        x_perp = math.cos(angle_rad)
        y_perp = -math.sin(angle_rad)

        # Right edge (+ sigma_y * 2)
        xr = x_center + 2.0 * sigma_y * x_perp
        yr = y_center + 2.0 * sigma_y * y_perp
        lat_r = lat + (yr / lat_km)
        lon_r = lon + (xr / lon_km)
        right_edge.append([lon_r, lat_r])

        # Left edge (- sigma_y * 2)
        xl = x_center - 2.0 * sigma_y * x_perp
        yl = y_center - 2.0 * sigma_y * y_perp
        lat_l = lat + (yl / lat_km)
        lon_l = lon + (xl / lon_km)
        left_edge.append([lon_l, lat_l])

    # Construct closed polygon coordinates: origin -> right edge -> tip -> left edge -> origin
    polygon_coords = [[lon, lat]] + right_edge + left_edge[::-1] + [[lon, lat]]

    return {
        "type": "Polygon",
        "coordinates": [polygon_coords],
        "wind_speed_ms": wind_speed_ms,
        "wind_deg": wind_deg
    }
