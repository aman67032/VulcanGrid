import os
import sys
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.dataset_generator import generate_tabular_dataset, CLASS_MAP, FEATURE_NAMES

def train_lightgbm_model():
    print("==================================================")
    print("       VulcanGrid: Training Tier 1 LightGBM       ")
    print("==================================================")

    # 1. Generate Synthetic Data
    X, y = generate_tabular_dataset(n_samples=5000, random_seed=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print(f"Dataset generated: {len(X_train)} train samples, {len(X_test)} test samples.")

    # 2. LightGBM Dataset
    train_data = lgb.Dataset(X_train, label=y_train, feature_name=FEATURE_NAMES)
    val_data = lgb.Dataset(X_test, label=y_test, feature_name=FEATURE_NAMES, reference=train_data)

    params = {
        'objective': 'multiclass',
        'num_class': 4,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'max_depth': 6,
        'feature_fraction': 0.8,
        'verbose': -1,
        'random_state': 42
    }

    # 3. Train Model
    model = lgb.train(
        params,
        train_data,
        num_boost_round=150,
        valid_sets=[train_data, val_data],
        callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)]
    )

    # 4. Predict & Evaluate
    preds_prob = model.predict(X_test)
    preds = np.argmax(preds_prob, axis=1)

    acc = accuracy_score(y_test, preds)
    target_names = [CLASS_MAP[i] for i in sorted(CLASS_MAP.keys())]

    print("\n[+] Model Evaluation Metrics:")
    print(f"Overall Accuracy: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y_test, preds, target_names=target_names))

    print("Confusion Matrix:")
    cm = confusion_matrix(y_test, preds)
    print(cm)

    # 5. Save Model
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "lgbm_model.txt")
    model.save_model(model_path)
    print(f"\n[+] Saved LightGBM model to: {model_path}")

    return acc, cm

if __name__ == "__main__":
    train_lightgbm_model()
