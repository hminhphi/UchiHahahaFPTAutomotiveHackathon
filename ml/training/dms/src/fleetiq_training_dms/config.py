"""Configuration settings for FleetIQ DMS Training & Two-Stage Bi-LSTM Model."""

from pathlib import Path
import torch


class Config:
    # -------------------------------------------------------------------------
    # PATHS (Relative to Repository Root)
    # -------------------------------------------------------------------------
    REPO_ROOT = Path(__file__).resolve().parents[5]
    DATA_ROOT = REPO_ROOT / "data" / "Practice_Dataset"

    # DMD Dataset (processed, ~70,641 frames)
    DMD_DATA_ROOT = REPO_ROOT / "data" / "DMD_Processed"

    FEATURE_DIR = REPO_ROOT / "artifacts" / "training" / "dms" / "extracted_features"
    OUTPUT_DIR = REPO_ROOT / "artifacts" / "models" / "dms"
    PRED_DIR = REPO_ROOT / "artifacts" / "predictions" / "dms"

    # -------------------------------------------------------------------------
    # PRACTICE DATASET TRIPS (Old - 3,600 frames)
    # -------------------------------------------------------------------------
    PRACTICE_TRIPS = [
        "T01-Sample",
        "T02-Sample",
        "T03-Sample",
        "T04-Sample",
        "T05-Sample",
        "T06-Sample",
    ]

    # -------------------------------------------------------------------------
    # DMD DATASET TRIPS (New - 70,641 frames)
    # -------------------------------------------------------------------------
    # Drowsiness sessions (15 trips - alert, drowsy, yawning)
    DMD_DROWSINESS_TRIPS = [
        "DMD-DROW-gA_1_s5_20190314_1426",
        "DMD-DROW-gA_5_s5_20190313_0906",
        "DMD-DROW-gB_10_s5_20190312_1035",
        "DMD-DROW-gB_10_s5_20190313_1417",
        "DMD-DROW-gB_6_s5_20190313_1337",
        "DMD-DROW-gB_7_s5_20190313_1355",
        "DMD-DROW-gB_9_s5_20190307_1631",
        "DMD-DROW-gC_13_s5_20190312_1003",
        "DMD-DROW-gC_14_s5_20190312_0918",
        "DMD-DROW-gF_23_s5_20190311_1019",
        "DMD-DROW-gF_23_s5_20190314_1349",
        "DMD-DROW-gZ_33_s5_20190404_0929",
        "DMD-DROW-gZ_33_s5_20190404_1502",
        "DMD-DROW-gZ_36_s5_20190409_1049",
        "DMD-DROW-gZ_37_s5_20190429_1206",
    ]

    # Distraction sessions (3 trips - alert, distracted)
    DMD_DISTRACTION_TRIPS = [
        "DMD-DIST-gA_1_s1_20190308_0931",
        "DMD-DIST-gA_1_s2_20190308_0921",
        "DMD-DIST-gA_1_s3_20190314_1431",
    ]

    DMD_ALL_TRIPS = DMD_DROWSINESS_TRIPS + DMD_DISTRACTION_TRIPS

    # -------------------------------------------------------------------------
    # TRAIN / VAL SPLIT (Combined Old + New)
    # -------------------------------------------------------------------------
    # Train: 5 Practice trips + 13 DMD drowsiness + 2 DMD distraction
    TRAIN_TRIPS = (
        [
            "T01-Sample",
            "T02-Sample",
            "T03-Sample",
            "T04-Sample",
            "T05-Sample",
        ]
        + [
            "DMD-DROW-gA_1_s5_20190314_1426",
            "DMD-DROW-gA_5_s5_20190313_0906",
            "DMD-DROW-gB_10_s5_20190312_1035",
            "DMD-DROW-gB_10_s5_20190313_1417",
            "DMD-DROW-gB_6_s5_20190313_1337",
            "DMD-DROW-gB_7_s5_20190313_1355",
            "DMD-DROW-gB_9_s5_20190307_1631",
            "DMD-DROW-gC_13_s5_20190312_1003",
            "DMD-DROW-gC_14_s5_20190312_0918",
            "DMD-DROW-gF_23_s5_20190311_1019",
            "DMD-DROW-gF_23_s5_20190314_1349",
            "DMD-DROW-gZ_33_s5_20190404_0929",
            "DMD-DROW-gZ_33_s5_20190404_1502",
        ]
        + [
            "DMD-DIST-gA_1_s1_20190308_0931",
            "DMD-DIST-gA_1_s2_20190308_0921",
        ]
    )

    # Val: 1 Practice trip + 2 DMD drowsiness + 1 DMD distraction
    VAL_TRIPS = [
        "T06-Sample",
        "DMD-DROW-gZ_36_s5_20190409_1049",
        "DMD-DROW-gZ_37_s5_20190429_1206",
        "DMD-DIST-gA_1_s3_20190314_1431",
    ]

    ALL_TRIPS = TRAIN_TRIPS + VAL_TRIPS

    # -------------------------------------------------------------------------
    # DATA ROOT MAPPING: trip_id -> data_root directory
    # -------------------------------------------------------------------------
    @classmethod
    def get_trip_dir(cls, trip_id: str) -> Path:
        """Return the directory path for a trip_id, supporting both data sources."""
        if trip_id.startswith("DMD-"):
            return cls.DMD_DATA_ROOT / trip_id
        else:
            return cls.DATA_ROOT / trip_id

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
    # CLASS WEIGHTING CONFIGURATION
    # -------------------------------------------------------------------------
    USE_CLASS_WEIGHTS = True
    CLASS_WEIGHT_POWER = 0.5  # Exponent factor for smoothed inverse class frequency

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
