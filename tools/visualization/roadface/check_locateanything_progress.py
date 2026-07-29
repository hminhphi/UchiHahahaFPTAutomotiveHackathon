from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from fleetiq_training_roadface.datasets import discover_trip_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report label2_custom relabel progress.")
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--output-dir-name", default="label2_custom")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = str(args.dataset_root) if args.dataset_root is not None else args.dataset
    rows: list[tuple[str, int, int, int, Counter[str]]] = []
    total_images = 0
    total_labels = 0
    total_objects = 0
    total_classes: Counter[str] = Counter()
    for trip in discover_trip_dirs(source):
        image_count = sum(
            1
            for path in (trip / "kitti" / "image_2").glob("*.*")
            if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stem.isdigit()
        )
        label_paths = [
            path
            for path in (trip / "kitti" / args.output_dir_name).glob("*.txt")
            if path.stem.isdigit()
        ]
        classes: Counter[str] = Counter()
        for path in label_paths:
            for line in path.read_text(encoding="utf-8").splitlines():
                fields = line.split()
                if fields:
                    classes[fields[0]] += 1
        object_count = sum(classes.values())
        rows.append((trip.name, image_count, len(label_paths), object_count, classes))
        total_images += image_count
        total_labels += len(label_paths)
        total_objects += object_count
        total_classes.update(classes)
    print(f"{'Trip':12} {'Frames':>7} {'Done':>7} {'Progress':>9} {'Objects':>8}")
    for trip, frames, done, objects, _ in rows:
        progress = 100.0 * done / max(frames, 1)
        print(f"{trip:12} {frames:7d} {done:7d} {progress:8.2f}% {objects:8d}")
    progress = 100.0 * total_labels / max(total_images, 1)
    print("-" * 49)
    print(f"{'TOTAL':12} {total_images:7d} {total_labels:7d} {progress:8.2f}% {total_objects:8d}")
    print("Classes:", ", ".join(f"{name}={count}" for name, count in sorted(total_classes.items())))


if __name__ == "__main__":
    main()
