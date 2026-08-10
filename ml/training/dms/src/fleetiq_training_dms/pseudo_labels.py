"""Reproducible DMS pseudo-labels derived only from measured face geometry."""

from __future__ import annotations

import numpy as np
import pandas as pd

STATE_MAP = {
    "alert": 0,
    "distracted": 1,
    "drowsy": 2,
    "microsleep": 3,
    "yawning": 4,
}


def apply_geometry_pseudo_labels(features: pd.DataFrame) -> pd.DataFrame:
    """Assign labels without reading organizer driver-state annotations."""
    result = features.copy()
    labels = np.full(len(result), -1, dtype=np.int64)
    sources = np.full(len(result), "excluded_no_face", dtype=object)
    if result.empty:
        result["state_label"] = labels
        result["label_source"] = sources
        return result

    face = result["face_detected"].fillna(False).astype(bool).to_numpy()
    # Prefer the extractor's 15-frame rolling signals so isolated landmark
    # jitter cannot create a DMS state or event window on its own.
    ear = _smoothed_or_raw(result, "ear_mean_5", "ear")
    mar = _smoothed_or_raw(result, "mar_mean_5", "mar")
    perclos = _column(result, "perclos")
    pitch = np.abs(_smoothed_or_raw(result, "pitch_mean_5", "pitch"))
    yaw = np.abs(_smoothed_or_raw(result, "yaw_mean_5", "yaw"))

    labels[face] = STATE_MAP["alert"]
    sources[face] = "geometry_rules_v1"
    drowsy = face & ((perclos >= 0.25) | (ear < 0.20))
    distracted = face & ((yaw >= 28.0) | (pitch >= 22.0))
    yawning = face & (mar >= 0.55)
    microsleep = face & ((perclos >= 0.55) | ((perclos >= 0.32) & (ear < 0.20)))
    labels[drowsy] = STATE_MAP["drowsy"]
    labels[distracted] = STATE_MAP["distracted"]
    labels[yawning] = STATE_MAP["yawning"]
    labels[microsleep] = STATE_MAP["microsleep"]
    result["state_label"] = labels
    result["label_source"] = sources
    return result


def normalize_pose_angle(value: float) -> float:
    """Resolve solvePnP's equivalent +/- 180-degree representation."""
    return float((value + 90.0) % 180.0 - 90.0)


def _column(features: pd.DataFrame, name: str) -> np.ndarray:
    return pd.to_numeric(features[name], errors="coerce").fillna(0.0).to_numpy()


def _smoothed_or_raw(features: pd.DataFrame, smoothed_name: str, raw_name: str) -> np.ndarray:
    """Use the legacy-named rolling column when present, otherwise raw test input."""
    return _column(features, smoothed_name if smoothed_name in features else raw_name)
