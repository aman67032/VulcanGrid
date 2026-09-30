import os
import sys
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.dataset_generator import generate_multispectral_patches, CLASS_MAP
from ml.cnn_model import HotspotPatchCNN

def train_cnn_model():
    print("==================================================")
    print("        VulcanGrid: Training Tier 2 PyTorch CNN   ")
    print("==================================================")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Generate Synthetic Multispectral Patches
    patches, labels = generate_multispectral_patches(n_samples=2400, patch_size=32, random_seed=42)

    X_train, X_test, y_train, y_test = train_test_split(
        patches, labels, test_size=0.2, random_state=42, stratify=labels
    )

    # 2. PyTorch DataLoaders
    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.long))
    test_dataset = TensorDataset(torch.tensor(X_test, dtype=torch.float32), torch.tensor(y_test, dtype=torch.long))

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    # 3. Initialize Model, Loss, Optimizer
    model = HotspotPatchCNN(num_classes=4).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)

    # 4. Training Loop
    epochs = 15
    model.train()
    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * batch_x.size(0)
        
        epoch_loss = running_loss / len(train_dataset)
        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch {epoch}/{epochs} - Train Loss: {epoch_loss:.4f}")

    # 5. Evaluation
    model.eval()
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            batch_x = batch_x.to(device)
            outputs = model(batch_x)
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(batch_y.numpy())

    acc = accuracy_score(all_targets, all_preds)
    target_names = [CLASS_MAP[i] for i in sorted(CLASS_MAP.keys())]

    print("\n[+] Model Evaluation Metrics:")
    print(f"Overall Accuracy: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(all_targets, all_preds, target_names=target_names))

    print("Confusion Matrix:")
    cm = confusion_matrix(all_targets, all_preds)
    print(cm)

    # 6. Save Model
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "cnn_model.pt")
    torch.save(model.state_dict(), model_path)
    print(f"\n[+] Saved CNN model weights to: {model_path}")

    return acc, cm

if __name__ == "__main__":
    train_cnn_model()
