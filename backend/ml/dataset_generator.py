import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

# Class mapping
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
    "land_cover_class",  # 0: Industrial, 1: Forest, 2: Solar Farm, 3: Agricultural/Barren
    "dist_to_solar_km",
    "persistence_7d",
    "hour_of_day"
]

def generate_tabular_dataset(n_samples: int = 4000, random_seed: int = 42) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Generates synthetic tabular features for 4 thermal hotspot classes.
    """
    np.random.seed(random_seed)
    samples_per_class = n_samples // 4

    dfs = []
    labels = []

    # 1. Controlled Industrial Flare
    # High FRP, high brightness, inside/near industrial facility, high persistence (refinery flare stack)
    frp_cf = np.random.gamma(shape=5, scale=8, size=samples_per_class) + 20.0  # 30-100+ MW
    b_cf = np.random.normal(340, 15, size=samples_per_class)
    b31_cf = np.random.normal(300, 8, size=samples_per_class)
    conf_cf = np.random.uniform(80, 100, size=samples_per_class)
    dist_ind_cf = np.random.exponential(scale=0.1, size=samples_per_class)  # Very close < 0.5 km
    inside_cf = (dist_ind_cf < 0.2).astype(int)
    lc_cf = np.zeros(samples_per_class, dtype=int)  # Industrial land cover
    dist_sol_cf = np.random.uniform(5, 50, size=samples_per_class)
    persist_cf = np.random.randint(5, 30, size=samples_per_class)  # High persistence
    hour_cf = np.random.randint(0, 24, size=samples_per_class)

    df_cf = pd.DataFrame({
        "frp": frp_cf, "brightness": b_cf, "bright_t31": b31_cf, "confidence": conf_cf,
        "dist_to_industrial_km": dist_ind_cf, "inside_facility": inside_cf,
        "land_cover_class": lc_cf, "dist_to_solar_km": dist_sol_cf,
        "persistence_7d": persist_cf, "hour_of_day": hour_cf
    })
    dfs.append(df_cf)
    labels.extend([0] * samples_per_class)

    # 2. Industrial Fire / Accident
    # Extremely high FRP, very high brightness, close to industrial facility, low/medium persistence
    frp_if = np.random.gamma(shape=7, scale=15, size=samples_per_class) + 50.0 # High intensity
    b_if = np.random.normal(365, 20, size=samples_per_class)
    b31_if = np.random.normal(315, 10, size=samples_per_class)
    conf_if = np.random.uniform(85, 100, size=samples_per_class)
    dist_ind_if = np.random.exponential(scale=0.3, size=samples_per_class)
    inside_if = (dist_ind_if < 0.3).astype(int)
    lc_if = np.zeros(samples_per_class, dtype=int)
    dist_sol_if = np.random.uniform(5, 50, size=samples_per_class)
    persist_if = np.random.randint(1, 5, size=samples_per_class)  # Sudden unexpected burst
    hour_if = np.random.randint(0, 24, size=samples_per_class)

    df_if = pd.DataFrame({
        "frp": frp_if, "brightness": b_if, "bright_t31": b31_if, "confidence": conf_if,
        "dist_to_industrial_km": dist_ind_if, "inside_facility": inside_if,
        "land_cover_class": lc_if, "dist_to_solar_km": dist_sol_if,
        "persistence_7d": persist_if, "hour_of_day": hour_if
    })
    dfs.append(df_if)
    labels.extend([1] * samples_per_class)

    # 3. Forest Fire / Wildfire
    # Variable high FRP, forest land cover, far from industrial, low persistence, active day/night
    frp_ff = np.random.gamma(shape=4, scale=12, size=samples_per_class) + 15.0
    b_ff = np.random.normal(335, 18, size=samples_per_class)
    b31_ff = np.random.normal(295, 12, size=samples_per_class)
    conf_ff = np.random.uniform(60, 95, size=samples_per_class)
    dist_ind_ff = np.random.uniform(5, 40, size=samples_per_class)  # Far from industry
    inside_ff = np.zeros(samples_per_class, dtype=int)
    lc_ff = np.ones(samples_per_class, dtype=int)  # Forest land cover
    dist_sol_ff = np.random.uniform(10, 60, size=samples_per_class)
    persist_ff = np.random.randint(1, 4, size=samples_per_class)
    hour_ff = np.random.randint(0, 24, size=samples_per_class)

    df_ff = pd.DataFrame({
        "frp": frp_ff, "brightness": b_ff, "bright_t31": b31_ff, "confidence": conf_ff,
        "dist_to_industrial_km": dist_ind_ff, "inside_facility": inside_ff,
        "land_cover_class": lc_ff, "dist_to_solar_km": dist_sol_ff,
        "persistence_7d": persist_ff, "hour_of_day": hour_ff
    })
    dfs.append(df_ff)
    labels.extend([2] * samples_per_class)

    # 4. False Alarm (Solar-farm glare / thermal reflection)
    # Low FRP, high brightness temp, daytime hours (10 to 16), inside/near solar farm polygon, zero persistence
    frp_fa = np.random.uniform(1.0, 8.0, size=samples_per_class)  # Very low FRP
    b_fa = np.random.normal(320, 10, size=samples_per_class)
    b31_fa = np.random.normal(310, 8, size=samples_per_class)
    conf_fa = np.random.uniform(30, 70, size=samples_per_class)
    dist_ind_fa = np.random.uniform(5, 50, size=samples_per_class)
    inside_fa = np.zeros(samples_per_class, dtype=int)
    lc_fa = np.full(samples_per_class, 2, dtype=int)  # Solar farm land cover
    dist_sol_fa = np.random.exponential(scale=0.2, size=samples_per_class)
    persist_fa = np.zeros(samples_per_class, dtype=int)  # Translucent transient glare
    hour_fa = np.random.randint(10, 17, size=samples_per_class)  # Peak solar hours only

    df_fa = pd.DataFrame({
        "frp": frp_fa, "brightness": b_fa, "bright_t31": b31_fa, "confidence": conf_fa,
        "dist_to_industrial_km": dist_ind_fa, "inside_facility": inside_fa,
        "land_cover_class": lc_fa, "dist_to_solar_km": dist_sol_fa,
        "persistence_7d": persist_fa, "hour_of_day": hour_fa
    })
    dfs.append(df_fa)
    labels.extend([3] * samples_per_class)

    X = pd.concat(dfs, ignore_index=True)
    y = np.array(labels)
    return X, y

def generate_multispectral_patches(n_samples: int = 2000, patch_size: int = 32, random_seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates synthetic 4-channel patches (SWIR, NIR, Red, NBR) of shape (n_samples, 4, 32, 32).
    NBR = (NIR - SWIR) / (NIR + SWIR + 1e-6)
    """
    np.random.seed(random_seed)
    samples_per_class = n_samples // 4

    patches = np.zeros((n_samples, 4, patch_size, patch_size), dtype=np.float32)
    labels = []

    for c in range(4):
        start_idx = c * samples_per_class
        end_idx = (c + 1) * samples_per_class

        for i in range(start_idx, end_idx):
            # Base background reflectance
            swir = np.random.normal(0.15, 0.03, (patch_size, patch_size))
            nir = np.random.normal(0.35, 0.05, (patch_size, patch_size))
            red = np.random.normal(0.10, 0.02, (patch_size, patch_size))

            # Center coordinates
            cx, cy = patch_size // 2, patch_size // 2
            y_grid, x_grid = np.ogrid[:patch_size, :patch_size]
            dist_sq = (x_grid - cx)**2 + (y_grid - cy)**2

            if c == 0:  # Controlled Flare: Pinpoint sharp SWIR spike in center
                swir_spike = 0.8 * np.exp(-dist_sq / 4.0)
                swir += swir_spike
            elif c == 1:  # Industrial Fire: Wide intense SWIR/NIR anomaly + smoke/burn plume
                swir_spike = 0.9 * np.exp(-dist_sq / 16.0)
                nir_dip = -0.2 * np.exp(-dist_sq / 25.0)
                swir += swir_spike
                nir += nir_dip
            elif c == 2:  # Forest Fire: Large negative NBR burn scar + active thermal perimeter
                swir_burn = 0.7 * np.exp(-dist_sq / 36.0)
                nir_veg_loss = -0.25 * np.exp(-dist_sq / 36.0)
                swir += swir_burn
                nir += nir_veg_loss
            elif c == 3:  # False Alarm: High NIR/Red specular panel reflectance, low SWIR spike
                glare = 0.4 * np.exp(-dist_sq / 64.0)
                nir += glare
                red += glare * 0.8

            # Clip values to realistic reflectance [0, 1]
            swir = np.clip(swir, 0, 1.0)
            nir = np.clip(nir, 0, 1.0)
            red = np.clip(red, 0, 1.0)

            # Calculate Normalized Burn Ratio (NBR)
            nbr = (nir - swir) / (nir + swir + 1e-6)

            patches[i, 0, :, :] = swir
            patches[i, 1, :, :] = nir
            patches[i, 2, :, :] = red
            patches[i, 3, :, :] = nbr

        labels.extend([c] * samples_per_class)

    return patches, np.array(labels)
