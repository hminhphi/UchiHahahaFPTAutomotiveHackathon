"""Evaluation script for Driver Sequence Model (Solution 2 Bi-LSTM)."""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import torch
from sklearn.metrics import classification_report, confusion_matrix

from fleetiq_training_dms.config import Config
from fleetiq_training_dms.dataset import FEATURE_COLS, get_temporal_block_dataloaders
from fleetiq_training_dms.model import build_sequence_model

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def evaluate_solution_2():
    print("=" * 70)
    print("EVALUATING SOLUTION 2: PRECISION, RECALL, F1-SCORE & CONFUSION MATRIX")
    print("=" * 70)

    # 1. Load Validation Dataloader (Temporal Block Split 80/20)
    _, val_loader, mean_scaler, std_scaler = get_temporal_block_dataloaders(
        Config.FEATURE_DIR, Config.ALL_TRIPS, seq_len=Config.SEQ_LEN, batch_size=Config.BATCH_SIZE, train_ratio=0.8
    )

    # 2. Load Checkpoint
    ckpt_path = Config.OUTPUT_DIR / "best_sequence_model.pt"
    if not ckpt_path.exists():
        print(f"[Error] Checkpoint not found at {ckpt_path}")
        return

    checkpoint = torch.load(ckpt_path, map_location=Config.DEVICE, weights_only=False)
    feature_dim = len(FEATURE_COLS)

    model = build_sequence_model(
        feature_dim=feature_dim,
        hidden_dim=Config.HIDDEN_DIM,
        num_layers=Config.NUM_LAYERS,
        num_classes=Config.NUM_CLASSES,
        cell_type=Config.MODEL_TYPE,
    ).to(Config.DEVICE)

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    y_true = []
    y_pred = []

    with torch.no_grad():
        for x, y, _, _ in val_loader:
            x = x.to(Config.DEVICE)
            logits = model(x)
            preds = torch.argmax(logits, dim=1).cpu().numpy()

            y_true.extend(y.numpy())
            y_pred.extend(preds)

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    class_names = [Config.STATE_INV_MAP[i] for i in range(Config.NUM_CLASSES)]

    # 3. Calculate Classification Report
    report = classification_report(y_true, y_pred, target_names=class_names, digits=4)
    print("\n📊 CLASSIFICATION REPORT (PRECISION, RECALL, F1-SCORE):")
    print("-" * 70)
    print(report)
    print("-" * 70)

    # 4. Confusion Matrix Table
    cm = confusion_matrix(y_true, y_pred)
    df_cm = pd.DataFrame(cm, index=[f"True: {c}" for c in class_names], columns=[f"Pred: {c}" for c in class_names])

    print("\n🧩 CONFUSION MATRIX:")
    print(df_cm)
    print("-" * 70)

    # 5. Plot Confusion Matrix
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("Confusion Matrix — Driver State Detection (Solution 2 Bi-LSTM)", fontsize=12, fontweight="bold")
    plt.colorbar()

    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45)
    plt.yticks(tick_marks, class_names)

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(
                j,
                i,
                format(cm[i, j], "d"),
                horizontalalignment="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=11,
                fontweight="bold",
            )

    plt.tight_layout()
    plt.ylabel("Thực tế (True Label)", fontsize=10, fontweight="bold")
    plt.xlabel("Dự đoán (Predicted Label)", fontsize=10, fontweight="bold")

    save_img_path = Config.OUTPUT_DIR / "confusion_matrix.png"
    plt.savefig(save_img_path, dpi=300)
    plt.close()
    print(f"\n🖼 Saved Confusion Matrix plot to: {save_img_path}")


def main():
    evaluate_solution_2()


if __name__ == "__main__":
    main()
