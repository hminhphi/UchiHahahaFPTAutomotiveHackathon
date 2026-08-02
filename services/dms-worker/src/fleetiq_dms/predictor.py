"""Two-Stage Hybrid Bi-LSTM Predictor for DMS Worker runtime."""

from pathlib import Path
from typing import Any
import numpy as np
import torch

from fleetiq_contracts.inference import DriverState
from fleetiq_training_dms.config import Config
from fleetiq_training_dms.dataset import FEATURE_COLS
from fleetiq_training_dms.model import build_sequence_model


class TwoStagePredictor:
    """Real-time sliding-window inference engine for Solution 2 Bi-LSTM model."""

    def __init__(self, checkpoint_path: str | Path | None = None, device: str = "cpu"):
        self.device = device
        self.seq_len = Config.SEQ_LEN
        self.feature_dim = len(FEATURE_COLS)
        self.model = build_sequence_model(
            feature_dim=self.feature_dim,
            hidden_dim=Config.HIDDEN_DIM,
            num_layers=Config.NUM_LAYERS,
            num_classes=Config.NUM_CLASSES,
            cell_type=Config.MODEL_TYPE,
        ).to(self.device)

        ckpt_path = Path(checkpoint_path) if checkpoint_path else Config.OUTPUT_DIR / "best_sequence_model.pt"
        self.mean_scaler: np.ndarray | None = None
        self.std_scaler: np.ndarray | None = None
        self.loaded = False

        if ckpt_path.exists():
            try:
                ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
                self.model.load_state_dict(ckpt["model_state_dict"])
                self.model.eval()
                self.mean_scaler = ckpt.get("mean_scaler", None)
                self.std_scaler = ckpt.get("std_scaler", None)
                self.loaded = True
            except Exception as e:
                print(f"[Warning] Failed to load TwoStagePredictor weights: {e}")

        # Trip feature buffers for sliding window
        self._trip_buffers: dict[str, list[np.ndarray]] = {}

    def predict_features(self, trip_id: str, raw_features: np.ndarray) -> DriverState:
        """Process a single frame feature vector and predict DriverState."""
        buf = self._trip_buffers.setdefault(trip_id, [])
        buf.append(raw_features)
        if len(buf) > self.seq_len:
            buf.pop(0)

        # Build window
        window_raw = np.array(buf, dtype=np.float32)
        if len(window_raw) < self.seq_len:
            pad_len = self.seq_len - len(window_raw)
            pad_frames = np.repeat(window_raw[:1], pad_len, axis=0)
            window_raw = np.vstack([pad_frames, window_raw])

        # Normalize
        if self.mean_scaler is not None and self.std_scaler is not None:
            norm_window = (window_raw - self.mean_scaler) / self.std_scaler
        else:
            m = np.mean(window_raw, axis=0, keepdims=True)
            s = np.std(window_raw, axis=0, keepdims=True) + 1e-6
            norm_window = (window_raw - m) / s

        x = torch.tensor(norm_window, dtype=torch.float32).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_idx = int(np.argmax(probs))
            conf = float(probs[pred_idx])

        state_str = Config.STATE_INV_MAP.get(pred_idx, "alert")

        # Extract sub-states from raw features if available (ear=0, mar=1, pitch=2)
        ear = float(raw_features[0]) if len(raw_features) > 0 else 0.25
        mar = float(raw_features[1]) if len(raw_features) > 1 else 0.20
        pitch = float(raw_features[2]) if len(raw_features) > 2 else 0.0

        eye_st = "closed" if ear < 0.18 else ("partial" if ear <= 0.25 else "open")
        mouth_st = "yawning" if mar > 0.55 else "normal"
        head_st = "down" if pitch < -12 else "normal"

        return DriverState(
            state=state_str,
            confidence=conf,
            eye_state=eye_st,
            head_pose=head_st,
            mouth_state=mouth_st,
        )

    def clear_trip(self, trip_id: str):
        """Clear buffer state for a trip."""
        self._trip_buffers.pop(trip_id, None)
