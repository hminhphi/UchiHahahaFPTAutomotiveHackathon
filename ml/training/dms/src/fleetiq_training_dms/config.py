"""Configuration settings for FleetIQ DMS Training & Two-Stage Bi-LSTM Model."""

from pathlib import Path
import torch


class Config:
    # -------------------------------------------------------------------------
    # PATHS (Relative to Repository Root)
    # -------------------------------------------------------------------------
    REPO_ROOT = Path(__file__).resolve().parents[5]
    DATA_ROOT = REPO_ROOT / "data" / "Practice_Dataset"

    FEATURE_DIR = REPO_ROOT / "artifacts" / "training" / "dms" / "extracted_features"
    OUTPUT_DIR = REPO_ROOT / "artifacts" / "models" / "dms"
    PRED_DIR = REPO_ROOT / "artifacts" / "predictions" / "dms"

    # Default trips for practice dataset training/eval
    TRAIN_TRIPS = ["T01-Sample", "T02-Sample", "T03-Sample", "T04-Sample", "T05-Sample"]
    VAL_TRIPS = ["T06-Sample"]
    ALL_TRIPS = [
        "T01-Sample",
        "T02-Sample",
        "T03-Sample",
        "T04-Sample",
        "T05-Sample",
        "T06-Sample",
    ]

    # -------------------------------------------------------------------------
    # TEMPORAL WINDOW CONFIGURATION
    # -------------------------------------------------------------------------
    # Sequence observation length: 20 frames ~ 1.0s at 20 FPS
    SEQ_LEN = 20

    # Model architecture type: 'lstm' or 'gru'
    MODEL_TYPE = "lstm"

    # -------------------------------------------------------------------------
    # LABEL MAPPINGS
    # -------------------------------------------------------------------------
    STATE_MAP = {
        "alert": 0,
        "distracted": 1,
        "drowsy": 2,
        "microsleep": 3,
        "yawning": 4,
    }
    STATE_INV_MAP = {v: k for k, v in STATE_MAP.items()}

    EYE_MAP = {"closed": 0, "open": 1, "partial": 2}
    HEAD_MAP = {"down": 0, "normal": 1, "side": 2}
    MOUTH_MAP = {"normal": 0, "yawning": 1}

    NUM_CLASSES = len(STATE_MAP)  # 5 classes

    # -------------------------------------------------------------------------
    # HYPERPARAMETERS
    # -------------------------------------------------------------------------
    HIDDEN_DIM = 128
    NUM_LAYERS = 2
    DROPOUT = 0.2

    BATCH_SIZE = 32
    LEARNING_RATE = 1e-3
    WEIGHT_DECAY = 1e-4
    EPOCHS = 20

    DEVICE = (
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )
