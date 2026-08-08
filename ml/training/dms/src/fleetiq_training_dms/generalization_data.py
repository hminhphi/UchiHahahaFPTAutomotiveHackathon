"""Data normalization helpers for subject-held-out DMS experiments."""

from pathlib import Path

import pandas as pd


CLASS_NAMES = ("attentive", "distracted", "drowsy")
REQUIRED_COLUMNS = {"image_path", "subject_id", "label"}


def normalize_label(raw_label: str) -> int | None:
    label = str(raw_label).strip().lower().replace(" ", "_")
    if label in {"alert", "attentive", "normal"}:
        return 0
    if label in {"distracted", "texting", "phone", "gaze_away"}:
        return 1
    if label in {"drowsy", "yawning", "microsleep", "sleepy_driving"}:
        return 2
    return None


def load_manifest(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"DMS manifest not found: {path}")
    records = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS - set(records.columns))
    if missing:
        raise ValueError(f"Manifest missing required columns: {', '.join(missing)}")

    records = records.copy()
    records["subject_id"] = records["subject_id"].astype(str)
    records["label"] = records["label"].map(normalize_label)
    records = records.dropna(subset=["label"]).copy()
    records["label"] = records["label"].astype("int64")
    records["image_path"] = records["image_path"].map(
        lambda value: str((path.parent / str(value)).resolve())
        if not Path(str(value)).is_absolute()
        else str(Path(str(value)).resolve())
    )
    if records.empty:
        raise ValueError(f"Manifest contains no supported labels: {path}")
    return records.reset_index(drop=True)


def subject_split(records: pd.DataFrame, validation_subject: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    validation_subject = str(validation_subject)
    validation = records[records["subject_id"].astype(str) == validation_subject].copy()
    train = records[records["subject_id"].astype(str) != validation_subject].copy()
    if train.empty or validation.empty:
        raise ValueError(f"Training or validation data is empty for validation subject {validation_subject}")
    return train.reset_index(drop=True), validation.reset_index(drop=True)
