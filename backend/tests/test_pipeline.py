import os
import sys
import pytest
import numpy as np

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.plume import calculate_gaussian_plume_polygon
from ml.dataset_generator import generate_tabular_dataset, generate_multispectral_patches
from app.services.inference import run_hotspot_inference

def test_tabular_dataset_generator():
    X, y = generate_tabular_dataset(n_samples=400, random_seed=42)
    assert len(X) == 400
    assert len(y) == 400
    assert set(np.unique(y)) == {0, 1, 2, 3}

def test_multispectral_patches_generator():
    patches, labels = generate_multispectral_patches(n_samples=40, patch_size=32, random_seed=42)
    assert patches.shape == (40, 4, 32, 32)
    assert len(labels) == 40

def test_gaussian_plume_calculation():
    plume = calculate_gaussian_plume_polygon(lat=22.35, lon=69.85, wind_speed_ms=5.0, wind_deg=225.0)
    assert plume["type"] == "Polygon"
    assert len(plume["coordinates"][0]) > 5

def test_inference_engine_execution():
    res = run_hotspot_inference(
        frp=65.0,
        brightness=345.0,
        bright_t31=300.0,
        confidence=95.0,
        dist_to_industrial_km=0.1,
        inside_facility=1,
        land_cover_class=0,
        dist_to_solar_km=25.0,
        persistence_7d=12,
        hour_of_day=14
    )
    assert "predicted_class" in res
    assert res["predicted_class"] in ["controlled_flare", "industrial_fire", "forest_fire", "false_alarm"]
    assert "shap_explanation" in res
    assert len(res["shap_explanation"]) == 5
    assert "patch_image_base64" in res
    assert res["patch_image_base64"].startswith("data:image/png;base64,")
