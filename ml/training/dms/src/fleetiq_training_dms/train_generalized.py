"""Subject-held-out multimodal DMS training for external RGB manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import timm
import torch
from PIL import Image
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset

from fleetiq_training_dms.config import Config
from fleetiq_training_dms.dataset import FEATURE_COLS
from fleetiq_training_dms.generalization_data import CLASS_NAMES, load_manifest, subject_split
from fleetiq_training_dms.model import VisualLandmarkGRU


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the subject-held-out multimodal DMS model")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--validation-subject", required=True)
    parser.add_argument("--epochs", type=int, default=Config.EPOCHS)
    parser.add_argument("--batch-size", type=int, default=Config.BATCH_SIZE)
    parser.add_argument("--sequence-length", type=int, default=Config.SEQ_LEN)
    parser.add_argument("--image-model", default="mobilenetv3_small_100")
    parser.add_argument("--device", default=Config.DEVICE)
    parser.add_argument("--output", type=Path, default=Config.OUTPUT_DIR / "generalized_best.pt")
    return parser.parse_args()


class SequenceWindowDataset(Dataset):
    def __init__(self, records: pd.DataFrame, sequence_length: int, transform):
        self.transform = transform
        self.windows: list[tuple[pd.DataFrame, int]] = []
        sort_columns = [column for column in ("frame_id", "timestamp") if column in records.columns]
        for _, subject_records in records.groupby("subject_id", sort=False):
            if sort_columns:
                subject_records = subject_records.sort_values(sort_columns)
            subject_records = subject_records.reset_index(drop=True)
            for end in range(sequence_length - 1, len(subject_records)):
                window = subject_records.iloc[end - sequence_length + 1 : end + 1]
                self.windows.append((window, int(window.iloc[-1]["label"])))

    def __len__(self) -> int:
        return len(self.windows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        window, label = self.windows[index]
        images = []
        for path in window["image_path"]:
            with Image.open(path) as image:
                images.append(self.transform(image.convert("RGB")))
        images = torch.stack(images)
        landmarks = torch.tensor(
            window.reindex(columns=FEATURE_COLS, fill_value=0.0).to_numpy(dtype=np.float32),
            dtype=torch.float32,
        )
        return images, landmarks, torch.tensor(label, dtype=torch.long)


def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    model.encoder.eval()
    total_loss = 0.0
    targets, predictions = [], []
    for images, landmarks, labels in loader:
        images, landmarks, labels = images.to(device), landmarks.to(device), labels.to(device)
        optimizer.zero_grad()
        logits = model(images, landmarks)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * labels.numel()
        predictions.extend(logits.detach().argmax(dim=1).cpu().tolist())
        targets.extend(labels.cpu().tolist())
    return total_loss / len(loader.dataset), f1_score(targets, predictions, average="macro", zero_division=0)


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    targets, predictions = [], []
    with torch.no_grad():
        for images, landmarks, labels in loader:
            logits = model(images.to(device), landmarks.to(device))
            total_loss += criterion(logits, labels.to(device)).item() * labels.numel()
            predictions.extend(logits.argmax(dim=1).cpu().tolist())
            targets.extend(labels.tolist())
    return total_loss / len(loader.dataset), f1_score(targets, predictions, average="macro", zero_division=0), targets


def main() -> None:
    args = parse_args()
    records = load_manifest(args.manifest)
    train_records, validation_records = subject_split(records, args.validation_subject)
    transform = timm.data.create_transform(input_size=224, is_training=False)
    train_set = SequenceWindowDataset(train_records, args.sequence_length, transform)
    validation_set = SequenceWindowDataset(validation_records, args.sequence_length, transform)
    if not train_set or not validation_set:
        raise ValueError(f"Sequence length {args.sequence_length} produces no train or validation windows")

    device = torch.device(args.device)
    model = VisualLandmarkGRU(image_model_name=args.image_model, pretrained=True).to(device)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=Config.LEARNING_RATE)
    criterion = torch.nn.CrossEntropyLoss()
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    validation_loader = DataLoader(validation_set, batch_size=args.batch_size)

    best_f1 = -1.0
    best_targets: list[int] = []
    history = []
    for epoch in range(1, args.epochs + 1):
        train_loss, train_f1 = train_one_epoch(model, train_loader, optimizer, criterion, device)
        validation_loss, validation_f1, validation_targets = evaluate(model, validation_loader, criterion, device)
        history.append({"epoch": epoch, "train_loss": train_loss, "train_macro_f1": train_f1, "validation_loss": validation_loss, "validation_macro_f1": validation_f1})
        print(f"Epoch {epoch:02d}/{args.epochs}: train_f1={train_f1:.4f} validation_f1={validation_f1:.4f}")
        if validation_f1 > best_f1:
            best_f1 = validation_f1
            best_targets = validation_targets
            args.output.parent.mkdir(parents=True, exist_ok=True)
            torch.save({"model_state_dict": model.state_dict(), "class_names": CLASS_NAMES, "validation_subject": str(args.validation_subject), "history": history}, args.output)

    metrics = {"macro_f1": best_f1, "class_support": {name: best_targets.count(index) for index, name in enumerate(CLASS_NAMES)}, "validation_subject": str(args.validation_subject), "class_names": CLASS_NAMES, "history": history}
    args.output.with_suffix(".json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Saved checkpoint: {args.output}")


if __name__ == "__main__":
    main()
