from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2

from scripts.roadface.roadface_lib import (
    CLASS_NAMES,
    CLASS_TO_ID,
    Detection,
    PRACTICE_ROOT,
    build_lane_corridor_masks,
    bbox_from_projected_object,
    compute_road_and_lane,
    detection_in_lane_corridor,
    discover_trips,
    parse_calibration,
    parse_kitti_labels,
)


DEFAULT_SPLIT = {
    "train": ["T01-Sample", "T02-Sample", "T03-Sample", "T04-Sample"],
    "val": ["T05-Sample"],
    "test": ["T06-Sample"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export projected KITTI 3D boxes as a YOLO road-facing dataset."
    )
    parser.add_argument("--dataset-root", type=Path, default=PRACTICE_ROOT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/roadface/yolo_dataset"),
    )
    parser.add_argument("--min-box-size", type=float, default=4.0)
    parser.add_argument("--lane-filter", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--lane-margin-m", type=float, default=0.25)
    parser.add_argument(
        "--link-mode",
        choices=("copy", "hardlink"),
        default="copy",
        help="Hardlink is faster but can fail across drives; copy is safest.",
    )
    return parser.parse_args()


def link_or_copy(src: Path, dst: Path, mode: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    if mode == "hardlink":
        try:
            os.link(src, dst)
            return
        except OSError:
            pass
    shutil.copy2(src, dst)


def trip_split(trip_name: str) -> str:
    for split, names in DEFAULT_SPLIT.items():
        if trip_name in names:
            return split
    return "train"


def export_trip(
    trip_dir: Path,
    output_dir: Path,
    min_box_size: float,
    link_mode: str,
    lane_filter: bool,
    lane_margin_m: float,
) -> dict[str, int]:
    split = trip_split(trip_dir.name)
    image_out_dir = output_dir / "images" / split
    label_out_dir = output_dir / "labels" / split
    stats = {"frames": 0, "frames_with_boxes": 0, "objects": 0, "skipped_off_lane": 0}
    for image_path in sorted((trip_dir / "kitti" / "image_2").glob("*.*")):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        frame_id = int(image_path.stem)
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        h, w = image.shape[:2]
        calib = parse_calibration(trip_dir / "kitti" / "calib" / f"{frame_id:06d}.txt")
        projection = calib.get("P2")
        if projection is None:
            continue
        _, _, _, line_segments = compute_road_and_lane(image)
        floor_mask, vertical_mask = build_lane_corridor_masks(image.shape, line_segments)
        rows: list[str] = []
        for obj in parse_kitti_labels(trip_dir / "kitti" / "label_2" / f"{frame_id:06d}.txt"):
            if obj.object_type not in CLASS_TO_ID:
                continue
            bbox = bbox_from_projected_object(obj, projection, w, h)
            if bbox is None or bbox[2] - bbox[0] < min_box_size or bbox[3] - bbox[1] < min_box_size:
                continue
            det = Detection(
                object_type=obj.object_type,
                bbox=bbox,
                dimensions=obj.dimensions,
                location=obj.location if obj.location[2] > 0.1 else None,
                rotation_y=obj.rotation_y,
                source="kitti_label",
            )
            if lane_filter and not detection_in_lane_corridor(
                det,
                floor_mask,
                vertical_mask,
                lateral_margin_m=lane_margin_m,
            ):
                stats["skipped_off_lane"] += 1
                continue
            x1, y1, x2, y2 = bbox
            cx = ((x1 + x2) / 2.0) / w
            cy = ((y1 + y2) / 2.0) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            rows.append(f"{CLASS_TO_ID[obj.object_type]} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        if not rows:
            continue
        out_name = f"{trip_dir.name}_{frame_id:06d}{image_path.suffix.lower()}"
        link_or_copy(image_path, image_out_dir / out_name, link_mode)
        (label_out_dir / f"{Path(out_name).stem}.txt").parent.mkdir(parents=True, exist_ok=True)
        (label_out_dir / f"{Path(out_name).stem}.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
        stats["frames"] += 1
        stats["frames_with_boxes"] += 1
        stats["objects"] += len(rows)
    return stats


def write_yaml(output_dir: Path) -> None:
    root = str(output_dir.resolve()).replace("\\", "/")
    names = "\n".join(f"  {idx}: {name}" for idx, name in enumerate(CLASS_NAMES))
    text = (
        f"path: {root}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "names:\n"
        f"{names}\n"
    )
    (output_dir / "dataset.yaml").write_text(text, encoding="utf-8")
    (output_dir / "split.json").write_text(json.dumps(DEFAULT_SPLIT, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    totals: dict[str, dict[str, int]] = {}
    for trip_dir in discover_trips(str(args.dataset_root)):
        if not trip_dir.name.endswith("-Sample"):
            continue
        totals[trip_dir.name] = export_trip(
            trip_dir,
            output_dir,
            args.min_box_size,
            args.link_mode,
            args.lane_filter,
            args.lane_margin_m,
        )
        print(f"{trip_dir.name}: {totals[trip_dir.name]}")
    write_yaml(output_dir)
    (output_dir / "export_stats.json").write_text(json.dumps(totals, indent=2), encoding="utf-8")
    print(f"Wrote YOLO dataset: {output_dir}")
    print(f"Dataset config: {output_dir / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
