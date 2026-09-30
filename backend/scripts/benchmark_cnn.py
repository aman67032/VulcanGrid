import os
import sys
import time
import numpy as np
import torch

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.cnn_model import HotspotPatchCNN, NumpyCNNForwardPass
from ml.dataset_generator import generate_multispectral_patches

def run_benchmark():
    print("==================================================")
    print("  VulcanGrid: CNN Inference Latency Benchmark     ")
    print("==================================================")

    device = torch.device("cpu")  # CPU baseline comparison
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))
    model_path = os.path.join(models_dir, "cnn_model.pt")

    pytorch_model = HotspotPatchCNN(num_classes=4)
    if os.path.exists(model_path):
        pytorch_model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"Loaded CNN weights from {model_path}")
    else:
        print("Model weights not found. Using randomly initialized weights for benchmark.")

    pytorch_model.eval().to(device)
    numpy_model = NumpyCNNForwardPass(pytorch_model)

    # Generate single test patch (4, 32, 32)
    patches, _ = generate_multispectral_patches(n_samples=40, patch_size=32, random_seed=99)
    test_patch = patches[0]

    iterations = 300

    # 1. Benchmark PyTorch (CPU)
    tensor_patch = torch.tensor(test_patch, dtype=torch.float32).unsqueeze(0).to(device)
    # Warmup
    for _ in range(20):
        with torch.no_grad():
            _ = pytorch_model(tensor_patch)

    start_pt = time.perf_counter()
    for _ in range(iterations):
        with torch.no_grad():
            _ = pytorch_model(tensor_patch)
    end_pt = time.perf_counter()

    pt_total_ms = (end_pt - start_pt) * 1000.0
    pt_avg_ms = pt_total_ms / iterations

    # 2. Benchmark NumPy Vectorized
    # Warmup
    for _ in range(20):
        _ = numpy_model.forward(test_patch)

    start_np = time.perf_counter()
    for _ in range(iterations):
        _ = numpy_model.forward(test_patch)
    end_np = time.perf_counter()

    np_total_ms = (end_np - start_np) * 1000.0
    np_avg_ms = np_total_ms / iterations

    print(f"\n[+] Benchmark Results ({iterations} single patch inferences):")
    print(f"    PyTorch (CPU):           {pt_avg_ms:.4f} ms / patch ({iterations / (pt_total_ms/1000):.1f} patches/sec)")
    print(f"    NumPy Vectorized (CPU):  {np_avg_ms:.4f} ms / patch ({iterations / (np_total_ms/1000):.1f} patches/sec)")
    print(f"    Latency Speedup Factor: {np_avg_ms / pt_avg_ms:.2f}x (PyTorch C++ backend optimized vs pure python numpy loops)")

    return pt_avg_ms, np_avg_ms

if __name__ == "__main__":
    run_benchmark()
