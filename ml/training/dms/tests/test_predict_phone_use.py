from pathlib import Path

import pandas as pd
import torch

from fleetiq_training_dms.dataset import FEATURE_COLS
from fleetiq_training_dms.predict import predict_sequence_trip


class StateModel(torch.nn.Module):
    def forward(self, value):
        return torch.tensor([[1.0, 0.0, 0.0, 0.0, 0.0]])


class PhoneDetector:
    def detect(self, image_path: Path):
        return True


def test_trip_prediction_emits_smoothed_phone_use(monkeypatch, tmp_path: Path):
    driver = tmp_path / "Phone-Test" / "driver"
    driver.mkdir(parents=True)
    for frame_id in range(3):
        (driver / f"frame_{frame_id:06d}.jpg").write_bytes(b"frame")
    features = pd.DataFrame(
        [
            {"frame_id": frame_id, "timestamp": frame_id / 20, **dict.fromkeys(FEATURE_COLS, 0.0)}
            for frame_id in range(3)
        ]
    )
    monkeypatch.setattr(
        "fleetiq_training_dms.predict.extract_features_from_trip",
        lambda *args, **kwargs: features,
    )

    result = predict_sequence_trip(
        StateModel(),
        driver.parent,
        seq_len=1,
        phone_detector=PhoneDetector(),
    )

    assert result["phone_use"].tolist() == [None, None, True]
