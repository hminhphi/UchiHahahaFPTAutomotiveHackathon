"""Export custom YOLO v3 predictions as KITTI labels for visual comparison.

The exporter intentionally writes to label2_yolo_v3, leaving the organizer
labels, LocateAnything labels, and pretrained YOLOP output unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
from fleetiq_data import DatasetPaths, discover_trips, resolve_trip
from fleetiq_roadface.yolo_detector import DEFAULT_MODEL_PATH, YoloDetector


DATASET_ROOTS = {
    "practice": Path("data/Practice_Dataset/Practice_Dataset"),
    "redacted": Path("data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write custom YOLO v3 predictions as KITTI-format labels."
    )
    parser.add_argument("--dataset", choices=DATASET_ROOTS, default="redacted")
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--trip", action="append", help="Trip ID; repeat as needed.")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--device", default="cuda:0", help="CUDA device or cpu")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--label-dir-name", default="label2_yolo_v3")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def selected_images(image_dir: Path, args: argparse.Namespace) -> list[Path]:
    images = [
        path
        for path in sorted(image_dir.iterdir())
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stem.isdigit()
    ]
    selected = [
        path
        for path in images
        if int(path.stem) >= args.start
        and (args.end is None or int(path.stem) <= args.end)
        and (int(path.stem) - args.start) % max(1, args.stride) == 0
    ]
    return selected[: args.max_frames] if args.max_frames is not None else selected


def kitti_line(label: str, bbox: tuple[float, float, float, float], confidence: float) -> str:
    x1, y1, x2, y2 = bbox
    return (
        f"{label} 0.00 0 -10.00 {x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f} "
        f"-1.00 -1.00 -1.00 -1000.00 -1000.00 -1000.00 -10.00 {confidence:.4f}"
    )


def write_labels(path: Path, detections: list) -> None:
    content = "\n".join(
        kitti_line(detection.object_type, detection.bbox, detection.confidence)
        for detection in detections
    )
    if content:
        content += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".txt.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    dataset_root = args.dataset_root or DATASET_ROOTS[args.dataset]
    if not dataset_root.is_dir():
        raise SystemExit(f"Dataset root not found: {dataset_root}")
    if not args.model.is_file():
        raise SystemExit(f"YOLO model not found: {args.model}")

    dataset = DatasetPaths(dataset_root)
    requested = {trip.casefold() for trip in args.trip or []}
    trips = [
        trip
        for trip in discover_trips(dataset)
        if not requested or trip.trip_id.casefold() in requested
    ]
    if not trips:
        raise SystemExit("No matching trips selected.")

    detector = YoloDetector(args.model, args.device, args.conf, args.iou)
    for discovered in trips:
        trip = resolve_trip(dataset, discovered.trip_id)
        images = selected_images(trip.image_2_dir, args)
        written = 0
        skipped = 0
        print(f"{trip.trip_id}: exporting {len(images)} frame(s) to {args.label_dir_name}")
        for image_path in images:
            label_path = trip.label_dir(args.label_dir_name) / f"{image_path.stem}.txt"
            if label_path.exists() and not args.overwrite:
                skipped += 1
                continue
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            write_labels(label_path, detector(image))
            written += 1
            if written == 1 or written % 50 == 0:
                print(f"  frame={image_path.stem} written={written} skipped={skipped}")
        print(f"{trip.trip_id}: completed written={written} skipped={skipped}")


if __name__ == "__main__":
    main()
