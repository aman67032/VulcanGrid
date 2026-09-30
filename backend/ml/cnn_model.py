import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class HotspotPatchCNN(nn.Module):
    """
    Compact 4-channel Multispectral CNN for Tier-2 Hotspot Validation.
    Input channels: [SWIR, NIR, Red, NBR] (32x32)
    Output: 4 class logits
    """
    def __init__(self, num_classes: int = 4):
        super(HotspotPatchCNN, self).__init__()
        self.conv1 = nn.Conv2d(in_channels=4, out_channels=16, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.pool = nn.MaxPool2d(2, 2)
        
        self.fc1 = nn.Linear(32 * 8 * 8, 64)
        self.fc2 = nn.Linear(64, num_classes)
        self.dropout = nn.Dropout(0.3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input shape: (B, 4, 32, 32)
        x = self.pool(F.relu(self.bn1(self.conv1(x))))  # (B, 16, 16, 16)
        x = self.pool(F.relu(self.bn2(self.conv2(x))))  # (B, 32, 8, 8)
        x = x.view(x.size(0), -1)  # Flatten
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class NumpyCNNForwardPass:
    """
    Vectorized Pure NumPy / SciPy forward pass of HotspotPatchCNN for low-overhead embedded latency comparison.
    """
    def __init__(self, pytorch_model: HotspotPatchCNN):
        # Extract weights from PyTorch model to NumPy arrays
        self.w_conv1 = pytorch_model.conv1.weight.detach().cpu().numpy()
        self.b_conv1 = pytorch_model.conv1.bias.detach().cpu().numpy()
        self.w_conv2 = pytorch_model.conv2.weight.detach().cpu().numpy()
        self.b_conv2 = pytorch_model.conv2.bias.detach().cpu().numpy()
        self.w_fc1 = pytorch_model.fc1.weight.detach().cpu().numpy()
        self.b_fc1 = pytorch_model.fc1.bias.detach().cpu().numpy()
        self.w_fc2 = pytorch_model.fc2.weight.detach().cpu().numpy()
        self.b_fc2 = pytorch_model.fc2.bias.detach().cpu().numpy()

    def _conv2d_simple(self, x: np.ndarray, weight: np.ndarray, bias: np.ndarray) -> np.ndarray:
        # x: (4, H, W), weight: (out_c, in_c, kh, kw)
        out_c, in_c, kh, kw = weight.shape
        _, h, w = x.shape
        padded = np.pad(x, ((0,0),(1,1),(1,1)), mode='constant')
        out = np.zeros((out_c, h, w), dtype=np.float32)
        for oc in range(out_c):
            for ic in range(in_c):
                for r in range(h):
                    for c_idx in range(w):
                        out[oc, r, c_idx] += np.sum(padded[ic, r:r+kh, c_idx:c_idx+kw] * weight[oc, ic])
            out[oc] += bias[oc]
        return out

    def _maxpool2d(self, x: np.ndarray) -> np.ndarray:
        c, h, w = x.shape
        out = np.zeros((c, h // 2, w // 2), dtype=np.float32)
        for oc in range(c):
            for r in range(0, h, 2):
                for col in range(0, w, 2):
                    out[oc, r//2, col//2] = np.max(x[oc, r:r+2, col:col+2])
        return out

    def forward(self, single_patch: np.ndarray) -> np.ndarray:
        # single_patch: (4, 32, 32)
        c1 = np.maximum(0, self._conv2d_simple(single_patch, self.w_conv1, self.b_conv1))
        p1 = self._maxpool2d(c1)
        c2 = np.maximum(0, self._conv2d_simple(p1, self.w_conv2, self.b_conv2))
        p2 = self._maxpool2d(c2)
        flat = p2.flatten()
        fc1_out = np.maximum(0, np.dot(self.w_fc1, flat) + self.b_fc1)
        fc2_out = np.dot(self.w_fc2, fc1_out) + self.b_fc2
        # Softmax
        exp_vals = np.exp(fc2_out - np.max(fc2_out))
        return exp_vals / np.sum(exp_vals)
