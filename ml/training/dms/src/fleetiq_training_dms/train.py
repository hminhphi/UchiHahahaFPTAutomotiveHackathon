"""Training pipeline for Driver Sequence Model (Two-Stage Bi-LSTM)."""

import time
import torch
import torch.nn as nn
import torch.optim as optim

from fleetiq_training_dms.config import Config
from fleetiq_training_dms.dataset import FEATURE_COLS, get_temporal_block_dataloaders
from fleetiq_training_dms.feature_extractor import extract_all_and_save
from fleetiq_training_dms.model import build_sequence_model


def train_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for x, y, _, _ in dataloader:
        x, y = x.to(device), y.to(device)

        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)

        loss.backward()
        optimizer.step()

        batch_size = x.size(0)
        running_loss += loss.item() * batch_size
        preds = torch.argmax(logits, dim=1)
        correct += (preds == y).sum().item()
        total += batch_size

    epoch_loss = running_loss / total
    epoch_acc = correct / total
    return epoch_loss, epoch_acc


def validate_epoch(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for x, y, _, _ in dataloader:
            x, y = x.to(device), y.to(device)

            logits = model(x)
            loss = criterion(logits, y)

            batch_size = x.size(0)
            running_loss += loss.item() * batch_size
            preds = torch.argmax(logits, dim=1)
            correct += (preds == y).sum().item()
            total += batch_size

    epoch_loss = running_loss / total
    epoch_acc = correct / total
    return epoch_loss, epoch_acc


def main():
    print("=" * 70)
    print(f"STARTING SOLUTION 2: TWO-STAGE TEMPORAL MODEL TRAINING ({Config.MODEL_TYPE.upper()})")
    print(f"Sequence Length (Window): {Config.SEQ_LEN} frames (~{Config.SEQ_LEN/20:.1f}s)")
    print(f"Device: {Config.DEVICE}")
    print("=" * 70)

    # 1. Trích xuất đặc trưng Stage 1 nếu chưa có
    extract_all_and_save()

    # 2. Tạo DataLoaders theo Temporal Block Split (80% past train / 20% future val per trip)
    train_loader, val_loader, mean_scaler, std_scaler = get_temporal_block_dataloaders(
        Config.FEATURE_DIR, Config.ALL_TRIPS, seq_len=Config.SEQ_LEN, batch_size=Config.BATCH_SIZE, train_ratio=0.8
    )

    feature_dim = len(FEATURE_COLS)

    # 3. Khởi tạo Model
    model = build_sequence_model(
        feature_dim=feature_dim,
        hidden_dim=Config.HIDDEN_DIM,
        num_layers=Config.NUM_LAYERS,
        num_classes=Config.NUM_CLASSES,
        cell_type=Config.MODEL_TYPE,
    ).to(Config.DEVICE)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=Config.LEARNING_RATE, weight_decay=Config.WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=Config.EPOCHS)

    best_val_acc = 0.0
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Vòng lặp huấn luyện
    for epoch in range(1, Config.EPOCHS + 1):
        t0 = time.time()
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, Config.DEVICE)
        val_loss, val_acc = validate_epoch(model, val_loader, criterion, Config.DEVICE)
        scheduler.step()
        elapsed = time.time() - t0

        print(f"Epoch [{epoch:02d}/{Config.EPOCHS:02d}] ({elapsed:.1f}s) | "
              f"Train Loss: {train_loss:.4f} - Acc: {train_acc:.4f} | "
              f"Val Loss: {val_loss:.4f} - Acc: {val_acc:.4f}")

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_path = Config.OUTPUT_DIR / "best_sequence_model.pt"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_acc": val_acc,
                "seq_len": Config.SEQ_LEN,
                "feature_dim": feature_dim,
                "mean_scaler": mean_scaler,
                "std_scaler": std_scaler,
            }, best_path)
            print(f"   --> Saved best checkpoint to: {best_path} (Val Acc: {best_val_acc:.4f})")

    print("\n" + "=" * 70)
    print(f"SOLUTION 2 TRAINING COMPLETE! Best Val Accuracy: {best_val_acc:.4f} ({best_val_acc*100:.2f}%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
