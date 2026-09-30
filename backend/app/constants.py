"""
VulcanGrid constants shared between training scripts and production inference.
Extracted here to avoid importing heavy ML training dependencies (pandas, etc.) in production.
"""

CLASS_MAP = {
    0: "controlled_flare",
    1: "industrial_fire",
    2: "forest_fire",
    3: "false_alarm"
}

REVERSE_CLASS_MAP = {v: k for k, v in CLASS_MAP.items()}

FEATURE_NAMES = [
    "frp",
    "brightness",
    "bright_t31",
    "confidence",
    "dist_to_industrial_km",
    "inside_facility",
    "land_cover_class",
    "dist_to_solar_km",
    "persistence_7d",
    "hour_of_day"
]
