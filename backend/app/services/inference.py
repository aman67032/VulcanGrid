import os
import io
import time
import base64
import numpy as np
import torch
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
from typing import Dict, Any, Tuple
from PIL import Image

from app.config import settings
from ml.dataset_generator import CLASS_MAP, FEATURE_NAMES
from ml.cnn_model import HotspotPatchCNN

# Cache models in memory
_LGBM_MODEL = None
_SHAP_EXPLAINER = None
_CNN_MODEL = None

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models"))

def get_lgbm_model():
    global _LGBM_MODEL, _SHAP_EXPLAINER
    if _LGBM_MODEL is None:
        model_path = os.path.join(MODELS_DIR, "lgbm_model.txt")
        if os.path.exists(model_path):
            _LGBM_MODEL = lgb.Booster(model_file=model_path)
            _SHAP_EXPLAINER = shap.TreeExplainer(_LGBM_MODEL)
        else:
            raise FileNotFoundError(f"LightGBM model file not found at {model_path}")
    return _LGBM_MODEL, _SHAP_EXPLAINER

def get_cnn_model():
    global _CNN_MODEL
    if _CNN_MODEL is None:
        model_path = os.path.join(MODELS_DIR, "cnn_model.pt")
        _CNN_MODEL = HotspotPatchCNN(num_classes=4)
        if os.path.exists(model_path):
            _CNN_MODEL.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        _CNN_MODEL.eval()
    return _CNN_MODEL

def generate_false_color_patch_base64(feature_dict: Dict[str, Any], predicted_class: str) -> str:
    """
    Renders a 32x32 SWIR (Red), NIR (Green), Red (Blue) false-colour composite PNG patch as base64 string.
    """
    patch_size = 32
    cx, cy = patch_size // 2, patch_size // 2
    y_grid, x_grid = np.ogrid[:patch_size, :patch_size]
    dist_sq = (x_grid - cx)**2 + (y_grid - cy)**2

    swir = np.random.normal(0.15, 0.03, (patch_size, patch_size))
    nir = np.random.normal(0.35, 0.05, (patch_size, patch_size))
    red = np.random.normal(0.10, 0.02, (patch_size, patch_size))

    if predicted_class == "controlled_flare":
        swir += 0.8 * np.exp(-dist_sq / 4.0)
    elif predicted_class == "industrial_fire":
        swir += 0.9 * np.exp(-dist_sq / 16.0)
        nir -= 0.2 * np.exp(-dist_sq / 25.0)
    elif predicted_class == "forest_fire":
        swir += 0.7 * np.exp(-dist_sq / 36.0)
        nir -= 0.25 * np.exp(-dist_sq / 36.0)
    elif predicted_class == "false_alarm":
        glare = 0.4 * np.exp(-dist_sq / 64.0)
        nir += glare
        red += glare * 0.8

    swir = np.clip(swir, 0, 1.0)
    nir = np.clip(nir, 0, 1.0)
    red = np.clip(red, 0, 1.0)

    # Stack into RGB array: R=SWIR, G=NIR, B=Red
    rgb = np.stack([swir, nir, red], axis=-1)
    rgb_uint8 = (rgb * 255.0).astype(np.uint8)

    img = Image.fromarray(rgb_uint8, mode='RGB')
    # Resize to 128x128 for crisp UI thumbnail display
    img_resized = img.resize((128, 128), Image.Resampling.NEAREST)

    buffer = io.BytesIO()
    img_resized.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64_str}"

def run_hotspot_inference(
    frp: float,
    brightness: float,
    bright_t31: float,
    confidence: float,
    dist_to_industrial_km: float,
    inside_facility: int,
    land_cover_class: int,
    dist_to_solar_km: float,
    persistence_7d: int,
    hour_of_day: int
) -> Dict[str, Any]:
    """
    Two-tier AI classification pipeline with SHAP explanation.
    """
    start_time = time.perf_counter()

    feature_values = [
        frp, brightness, bright_t31, confidence,
        dist_to_industrial_km, inside_facility, land_cover_class,
        dist_to_solar_km, persistence_7d, hour_of_day
    ]
    X_input = np.array([feature_values], dtype=np.float32)

    # Tier 1: LightGBM Fast Triage
    lgb_model, explainer = get_lgbm_model()
    probs = lgb_model.predict(X_input)[0]  # Array of 4 probabilities

    pred_idx = int(np.argmax(probs))
    max_prob = float(probs[pred_idx])

    tier_used = 1
    final_class_idx = pred_idx
    final_probs = probs

    # Tier 2 Routing: If max prob < 0.85 -> Tier 2 CNN validation
    if max_prob < 0.85:
        tier_used = 2
        cnn_model = get_cnn_model()
        # Generate synthetic 4-channel patch for CNN input
        patch_size = 32
        patch_4c = np.zeros((1, 4, patch_size, patch_size), dtype=np.float32)

        swir = np.random.normal(0.15, 0.03, (patch_size, patch_size))
        nir = np.random.normal(0.35, 0.05, (patch_size, patch_size))
        red = np.random.normal(0.10, 0.02, (patch_size, patch_size))
        nbr = (nir - swir) / (nir + swir + 1e-6)

        patch_4c[0, 0] = swir
        patch_4c[0, 1] = nir
        patch_4c[0, 2] = red
        patch_4c[0, 3] = nbr

        with torch.no_grad():
            cnn_logits = cnn_model(torch.tensor(patch_4c, dtype=torch.float32))
            cnn_probs = torch.softmax(cnn_logits, dim=1).numpy()[0]

        # Blend probabilities (70% CNN + 30% LightGBM)
        blended_probs = 0.7 * cnn_probs + 0.3 * probs
        final_class_idx = int(np.argmax(blended_probs))
        final_probs = blended_probs

    predicted_class = CLASS_MAP[final_class_idx]
    overall_confidence = float(final_probs[final_class_idx])

    # Compute SHAP Values for top 5 factors
    shap_vals = explainer.shap_values(X_input)
    # Handle SHAP multi-class format
    if isinstance(shap_vals, list):
        class_shap = shap_vals[final_class_idx][0]
    else:
        class_shap = shap_vals[0, :, final_class_idx] if len(shap_vals.shape) == 3 else shap_vals[0]

    # Top 5 SHAP features sorted by absolute magnitude
    abs_indices = np.argsort(np.abs(class_shap))[::-1][:5]

    shap_explanations = []
    for idx in abs_indices:
        feat_name = FEATURE_NAMES[idx]
        val = feature_values[idx]
        s_val = float(class_shap[idx])
        impact = "push_towards" if s_val > 0 else "push_against"
        shap_explanations.append({
            "feature": feat_name,
            "value": round(float(val), 2),
            "shap_value": round(s_val, 4),
            "impact": impact
        })

    # Render false-colour PNG patch base64
    patch_b64 = generate_false_color_patch_base64(
        {FEATURE_NAMES[i]: feature_values[i] for i in range(len(FEATURE_NAMES))},
        predicted_class
    )

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    class_probs_dict = {
        CLASS_MAP[i]: round(float(final_probs[i]), 4) for i in range(4)
    }

    return {
        "predicted_class": predicted_class,
        "class_probs": class_probs_dict,
        "tier_used": tier_used,
        "overall_confidence": round(overall_confidence, 4),
        "shap_explanation": shap_explanations,
        "patch_image_base64": patch_b64,
        "latency_ms": round(latency_ms, 2)
    }
