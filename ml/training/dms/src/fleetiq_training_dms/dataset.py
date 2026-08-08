"""PyTorch Dataset & Temporal Block Split DataLoader for Driver Sequence Model."""

from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

FEATURE_COLS = [
    "ear", "mar", "pitch", "yaw", "roll",
    "delta_ear", "delta_mar", "delta_pitch", "delta_yaw", "delta_roll",
    "ear_mean_5", "ear_std_5", "mar_mean_5", "pitch_mean_5", "yaw_mean_5",
    "brightness", "motion_mean", "motion_std",
]


class DriverSequenceDataset(Dataset):
    """PyTorch dataset for N-frame sliding window driver state classification."""

    def __init__(self, sequences, labels, meta, is_train=True, augment=False):
        self.sequences = sequences
        self.labels = labels
        self.meta = meta
        self.is_train = is_train
        self.augment = augment

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq = self.sequences[idx].copy()

        if self.is_train and self.augment:
            noise = np.random.normal(0, 0.015, size=seq.shape).astype(np.float32)
            seq = seq + noise

        x = torch.tensor(seq, dtype=torch.float32)
        y = torch.tensor(self.labels[idx], dtype=torch.long)
        trip_id, frame_id, ts = self.meta[idx]
        return x, y, frame_id, trip_id


def get_temporal_block_dataloaders(
    feature_dir: str | Path,
    trip_ids: list[str],
    seq_len: int = 20,
    batch_size: int = 32,
    train_ratio: float = 0.8,
) -> tuple[DataLoader, DataLoader, np.ndarray, np.ndarray]:
    """Split time-series data per trip: 80% past -> Train, 20% future -> Validation."""
    feature_dir = Path(feature_dir)

    trip_dfs = []
    for trip_id in trip_ids:
        csv_path = feature_dir / f"{trip_id}_features.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            trip_dfs.append(df)

    if not trip_dfs:
        raise FileNotFoundError(f"No feature CSV files found in {feature_dir}")

    full_df = pd.concat(trip_dfs, ignore_index=True)
    raw_feats = full_df[FEATURE_COLS].values.astype(np.float32)

    mean = np.mean(raw_feats, axis=0, keepdims=True)
    std = np.std(raw_feats, axis=0, keepdims=True) + 1e-6
    normalized_feats = (raw_feats - mean) / std

    train_seqs, train_lbls, train_meta = [], [], []
    val_seqs, val_lbls, val_meta = [], [], []

    curr_idx = 0
    for df in trip_dfs:
        n_samples = len(df)
        feats = normalized_feats[curr_idx : curr_idx + n_samples]
        lbls = df["state_label"].values.astype(np.int64)
        frame_ids = df["frame_id"].values
        timestamps = df["timestamp"].values
        trip_id = df["frame_id"].iloc[0] if "trip_id" not in df else df["trip_id"].iloc[0]

        split_idx = int(n_samples * train_ratio)

        for i in range(n_samples):
            start_idx = max(0, i - seq_len + 1)
            seq_window = feats[start_idx : i + 1]

            if len(seq_window) < seq_len:
                pad_len = seq_len - len(seq_window)
                pad_frames = np.repeat(seq_window[:1], pad_len, axis=0)
                seq_window = np.vstack([pad_frames, seq_window])

            if i < split_idx:
                train_seqs.append(seq_window)
                train_lbls.append(lbls[i])
                train_meta.append((trip_id, frame_ids[i], timestamps[i]))
            elif i >= split_idx + seq_len:
                val_seqs.append(seq_window)
                val_lbls.append(lbls[i])
                val_meta.append((trip_id, frame_ids[i], timestamps[i]))

        curr_idx += n_samples

    train_ds = DriverSequenceDataset(np.array(train_seqs), np.array(train_lbls), train_meta, is_train=True, augment=True)
    val_ds = DriverSequenceDataset(np.array(val_seqs), np.array(val_lbls), val_meta, is_train=False, augment=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, pin_memory=torch.cuda.is_available())
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())

    print(f"[TemporalBlockDataset] Train samples: {len(train_ds)} | Val samples: {len(val_ds)}")

    return train_loader, val_loader, mean, std
