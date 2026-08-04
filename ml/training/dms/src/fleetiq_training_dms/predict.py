"""Inference pipeline for Solution 2 Driver Sequence Model."""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

import torch

from fleetiq_training_dms.config import Config
from fleetiq_training_dms.dataset import FEATURE_COLS
from fleetiq_training_dms.feature_extractor import extract_features_from_trip
from fleetiq_training_dms.model import build_sequence_model
from fleetiq_training_dms.phone_detector import PhoneUseDetector, PhoneUseSmoother


def predict_sequence_trip(
    model: torch.nn.Module,
    trip_dir: str | Path,
    seq_len: int = 20,
    mean_scaler: np.ndarray | None = None,
    std_scaler: np.ndarray | None = None,
    device: str = "cpu",
    phone_detector: PhoneUseDetector | None = None,
) -> pd.DataFrame:
    """Run sequence prediction on a single trip directory."""
    trip_dir = Path(trip_dir)
    trip_id = trip_dir.name

    feat_csv = Config.FEATURE_DIR / f"{trip_id}_features.csv"
    if feat_csv.exists():
        df_feat = pd.read_csv(feat_csv)
    else:
        df_feat = extract_features_from_trip(trip_dir, is_train=False)

    raw_feats = df_feat[FEATURE_COLS].values.astype(np.float32)
    if mean_scaler is not None and std_scaler is not None:
        feats = (raw_feats - mean_scaler) / std_scaler
    else:
        m = np.mean(raw_feats, axis=0, keepdims=True)
        s = np.std(raw_feats, axis=0, keepdims=True) + 1e-6
        feats = (raw_feats - m) / s

    n_samples = len(df_feat)
    results = []
    model.eval()
    phone_smoother = PhoneUseSmoother()

    with torch.no_grad():
        for i in range(n_samples):
            start_idx = max(0, i - seq_len + 1)
            seq_window = feats[start_idx : i + 1]

            if len(seq_window) < seq_len:
                pad_len = seq_len - len(seq_window)
                pad_frames = np.repeat(seq_window[:1], pad_len, axis=0)
                seq_window = np.vstack([pad_frames, seq_window])

            x = torch.tensor(seq_window, dtype=torch.float32).unsqueeze(0).to(device)
            logits = model(x)
            pred_idx = torch.argmax(logits, dim=1).item()
            pred_state = Config.STATE_INV_MAP.get(pred_idx, "alert")
            frame_id = int(df_feat.iloc[i]["frame_id"])
            raw_phone_use = (
                phone_detector.detect(
                    trip_dir / "driver" / f"frame_{frame_id:06d}.jpg"
                )
                if phone_detector is not None
                else None
            )

            results.append({
                "frame_id": frame_id,
                "timestamp": df_feat.iloc[i]["timestamp"],
                "predicted_driver_state": pred_state,
                "phone_use": phone_smoother.update(raw_phone_use),
            })

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Run Solution 2 (Two-Stage Bi-LSTM) prediction for a trip")
    parser.add_argument("--trip-dir", type=str, required=True, help="Path to trip directory")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint .pt file")
    parser.add_argument("--phone-model", type=Path, default=Path("yolo11n.pt"))
    parser.add_argument("--phone-confidence", type=float, default=0.40)
    parser.add_argument("--output", type=str, default=None, help="Path to output CSV file")
    args = parser.parse_args()

    trip_dir = Path(args.trip_dir)
    trip_id = trip_dir.name

    feature_dim = len(FEATURE_COLS)
    model = build_sequence_model(
        feature_dim=feature_dim,
        hidden_dim=Config.HIDDEN_DIM,
        num_layers=Config.NUM_LAYERS,
        num_classes=Config.NUM_CLASSES,
        cell_type=Config.MODEL_TYPE,
    ).to(Config.DEVICE)

    ckpt_path = Path(args.checkpoint) if args.checkpoint else Config.OUTPUT_DIR / "best_sequence_model.pt"

    mean_scaler = None
    std_scaler = None

    if ckpt_path.exists():
        print(f"[Solution 2 Predict] Loading weights from: {ckpt_path}")
        ckpt = torch.load(ckpt_path, map_location=Config.DEVICE, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        mean_scaler = ckpt.get("mean_scaler", None)
        std_scaler = ckpt.get("std_scaler", None)
    else:
        print(f"[Warning] Checkpoint {ckpt_path} not found. Running with default weights.")

    phone_detector = PhoneUseDetector(args.phone_model, confidence=args.phone_confidence)
    df_pred = predict_sequence_trip(
        model,
        trip_dir,
        seq_len=Config.SEQ_LEN,
        mean_scaler=mean_scaler,
        std_scaler=std_scaler,
        device=Config.DEVICE,
        phone_detector=phone_detector,
    )

    out_path = Path(args.output) if args.output else Config.PRED_DIR / f"{trip_id}_twostage.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df_pred.to_csv(out_path, index=False)
    print(f"[Solution 2 Predict] Saved predictions to: {out_path}")
    print(df_pred.head(10))


if __name__ == "__main__":
    main()
