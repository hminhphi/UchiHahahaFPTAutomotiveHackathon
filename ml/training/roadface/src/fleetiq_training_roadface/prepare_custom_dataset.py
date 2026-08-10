"""Export label2_custom (LocateAnything) annotations as a YOLO dataset.

Split strategy: per-trip temporal 80 / 10 / 10.
  - Each trip contributes 80% of its frames to train, next 10% to val,
    last 10% to test.
  - This ensures every shooting condition (trip) is represented in all
    three splits, rather than whole trips being held out (which would
    bias val/test to specific conditions).

Usage:
    uv run --package fleetiq-training-roadface python -m \\
        fleetiq_training_roadface.prepare_custom_dataset \\
        --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted \\
        --output-dir artifacts/training/roadface/yolo_dataset_detached \\
        --link-mode hardlink

    # Also include Practice trips (they also have label2_custom):
    uv run --package fleetiq-training-roadface python -m \\
        fleetiq_training_roadface.prepare_custom_dataset \\
        --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted \\
        --extra-root data/Practice_Dataset/Practice_Dataset \\
        --output-dir artifacts/training/roadface/yolo_dataset_combined \\
        --link-mode hardlink
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path


LABEL2_CLASS_NAMES = [
    "Car",
    "Bus",
    "LongVehicle",
    "Motorcycle",
    "Cyclist",
    "Pedestrian",
]
LABEL2_CLASS_TO_ID = {name: idx for idx, name in enumerate(LABEL2_CLASS_NAMES)}

# Temporal split fractions per trip (train / val / test).
TRAIN_FRAC = 0.80
VAL_FRAC = 0.10
# TEST_FRAC = remaining (0.10)


def parse_kitti_2d_line(line: str) -> tuple[str, tuple[float, float, float, float]] | None:
    parts = line.strip().split()
    if len(parts) < 8:
        return None
    object_type = parts[0]
    if object_type == "DontCare":
        return None
    try:
        x1, y1, x2, y2 = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
    except (ValueError, IndexError):
        return None
    return object_type, (x1, y1, x2, y2)


def frame_split(frame_index: int, total_frames: int) -> str:
    """Return 'train', 'val', or 'test' for a frame based on its temporal position."""
    train_end = int(total_frames * TRAIN_FRAC)
    val_end = train_end + int(total_frames * VAL_FRAC)
    if frame_index < train_end:
        return "train"
    if frame_index < val_end:
        return "val"
    return "test"


def export_trip(trip_dir: Path, output_dir: Path, min_box_size: float, link_mode: str) -> dict[str, dict[str, int]]:
    label2_dir = trip_dir / "kitti" / "label2_custom"
    image_dir = trip_dir / "kitti" / "image_2"

    if not label2_dir.is_dir():
        print(f"  SKIP {trip_dir.name}: no label2_custom directory")
        return {}

    # Collect all labeled frames sorted by frame ID.
    label_files = sorted(
        (p for p in label2_dir.glob("*.txt") if p.stem.isdigit()),
        key=lambda p: int(p.stem),
    )
    total = len(label_files)
    if total == 0:
        print(f"  SKIP {trip_dir.name}: label2_custom is empty")
        return {}

    stats: dict[str, dict[str, int]] = {
        "train": {"frames": 0, "objects": 0},
        "val": {"frames": 0, "objects": 0},
        "test": {"frames": 0, "objects": 0},
    }

    for list_index, label_path in enumerate(label_files):
        frame_id = label_path.stem
        split = frame_split(list_index, total)

        image_path = image_dir / f"{frame_id}.jpg"
        if not image_path.is_file():
            image_path = image_dir / f"{frame_id}.png"
        if not image_path.is_file():
            continue

        # Read image dimensions without loading pixel data (use OpenCV header).
        import cv2
        img = cv2.imread(str(image_path))
        if img is None:
            continue
        h, w = img.shape[:2]

        rows: list[str] = []
        for line in label_path.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            parsed = parse_kitti_2d_line(line)
            if parsed is None:
                continue
            object_type, (x1, y1, x2, y2) = parsed
            if object_type not in LABEL2_CLASS_TO_ID:
                continue
            bw = x2 - x1
            bh = y2 - y1
            if bw < min_box_size or bh < min_box_size:
                continue
            cx = ((x1 + x2) / 2.0) / w
            cy = ((y1 + y2) / 2.0) / h
            rows.append(
                f"{LABEL2_CLASS_TO_ID[object_type]} {cx:.6f} {cy:.6f} "
                f"{bw / w:.6f} {bh / h:.6f}"
            )

        if not rows:
            continue

        out_name = f"{trip_dir.name}_{frame_id}{image_path.suffix.lower()}"
        img_dst = output_dir / "images" / split / out_name
        img_dst.parent.mkdir(parents=True, exist_ok=True)
        lbl_dst = output_dir / "labels" / split / f"{Path(out_name).stem}.txt"
        lbl_dst.parent.mkdir(parents=True, exist_ok=True)

        if link_mode == "hardlink":
            try:
                if not img_dst.exists():
                    os.link(image_path, img_dst)
            except OSError:
                shutil.copy2(image_path, img_dst)
        else:
            shutil.copy2(image_path, img_dst)

        lbl_dst.write_text("\n".join(rows) + "\n", encoding="utf-8")
        stats[split]["frames"] += 1
        stats[split]["objects"] += len(rows)

    return stats


def write_yaml(output_dir: Path) -> None:
    root = str(output_dir.resolve()).replace("\\", "/")
    names = "\n".join(f"  {idx}: {name}" for idx, name in enumerate(LABEL2_CLASS_NAMES))
    text = (
        f"path: {root}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "names:\n"
        f"{names}\n"
        f"nc: {len(LABEL2_CLASS_NAMES)}\n"
    )
    (output_dir / "dataset.yaml").write_text(text, encoding="utf-8")


def discover_trip_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and (d / "kitti" / "label2_custom").is_dir()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export label2_custom labels to YOLO dataset (80/10/10 per-trip split).")
    parser.add_argument("--dataset-root", type=Path, required=True, help="Primary dataset root (e.g. Hackathon detached).")
    parser.add_argument("--extra-root", type=Path, default=None, help="Optional second root (e.g. Practice trips).")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/training/roadface/yolo_dataset_detached"))
    parser.add_argument("--min-box-size", type=float, default=4.0)
    parser.add_argument("--link-mode", choices=("copy", "hardlink"), default="copy")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    roots = [args.dataset_root]
    if args.extra_root is not None:
        roots.append(args.extra_root)

    trip_dirs: list[Path] = []
    for root in roots:
        trip_dirs.extend(discover_trip_dirs(root))

    if not trip_dirs:
        print("No trips with label2_custom found.")
        return

    print(f"Exporting {len(trip_dirs)} trips with 80/10/10 temporal split per trip...")

    all_stats: dict[str, dict[str, dict[str, int]]] = {}
    totals: dict[str, dict[str, int]] = {
        "train": {"frames": 0, "objects": 0},
        "val": {"frames": 0, "objects": 0},
        "test": {"frames": 0, "objects": 0},
    }

    for trip_dir in trip_dirs:
        trip_stats = export_trip(trip_dir, output_dir, args.min_box_size, args.link_mode)
        if not trip_stats:
            continue
        all_stats[trip_dir.name] = trip_stats
        for split, counts in trip_stats.items():
            totals[split]["frames"] += counts["frames"]
            totals[split]["objects"] += counts["objects"]
        print(
            f"  {trip_dir.name}: "
            f"train={trip_stats['train']['frames']}f/{trip_stats['train']['objects']}obj  "
            f"val={trip_stats['val']['frames']}f/{trip_stats['val']['objects']}obj  "
            f"test={trip_stats['test']['frames']}f/{trip_stats['test']['objects']}obj"
        )

    write_yaml(output_dir)
    (output_dir / "export_stats.json").write_text(json.dumps(all_stats, indent=2), encoding="utf-8")

    print()
    print("Totals:")
    for split in ("train", "val", "test"):
        print(f"  {split}: {totals[split]['frames']} frames, {totals[split]['objects']} objects")
    print(f"\nDataset written to: {output_dir}")
    print(f"Config: {output_dir / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
