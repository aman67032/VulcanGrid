import math
import numpy as np
from typing import Dict, Any, List

def calculate_gaussian_plume_polygon(
    lat: float,
    lon: float,
    wind_speed_ms: float = 4.5,
    wind_deg: float = 225.0,  # Direction wind is coming FROM (225 = SW, so plume blows NE)
    plume_length_km: float = 5.0,
    max_width_km: float = 1.2,
    num_points: int = 20
) -> Dict[str, Any]:
    """
    Computes a 2D Gaussian plume dispersion polygon emanating from a hotspot (lat, lon).
    Returns GeoJSON Geometry Polygon dict.
    """
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
        "coordinates": [polygon_coords]
    }
