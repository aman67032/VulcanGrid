import os
import sys
import numpy as np
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.cnn_model import HotspotPatchCNN

def export_weights():
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))
    pt_path = os.path.join(models_dir, "cnn_model.pt")
    npz_path = os.path.join(models_dir, "cnn_weights.npz")

    model = HotspotPatchCNN(num_classes=4)
    if os.path.exists(pt_path):
        model.load_state_dict(torch.load(pt_path, map_location=torch.device("cpu")))

    state_dict = model.state_dict()
    np_weights = {k: v.detach().cpu().numpy() for k, v in state_dict.items()}

    np.savez_compressed(npz_path, **np_weights)
    print(f"Successfully exported 50KB NumPy compressed weights to: {npz_path}")

if __name__ == "__main__":
    export_weights()
