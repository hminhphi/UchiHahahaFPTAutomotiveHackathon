from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from fleetiq_training_roadface.experimental import (
    bbox_from_projected_object,
    discover_trips,
    find_image,
    iou,
    load_trip_doc,
    parse_calibration,
    parse_kitti_labels,
    read_image,
    safe_float,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate road-facing object distance/TTC outputs on full-GT practice trips."
    )
    parser.add_argument("--pred-dir", type=Path, default=Path("artifacts/roadface/predictions"))
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Explicit trip root; otherwise use FLEETIQ_DATA_ROOT or Practice data.",
    )
    parser.add_argument("--trip", action="append")
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path("artifacts/roadface/evaluation_summary.json"))
    return parser.parse_args()


def read_predictions(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def gt_objects(trip_dir: Path, frame_id: int) -> list[dict[str, float | str]]:
    image = read_image(find_image(trip_dir / "kitti" / "image_2", f"{frame_id:06d}"))
    if image is None:
        return []
    h, w = image.shape[:2]
    calib = parse_calibration(trip_dir / "kitti" / "calib" / f"{frame_id:06d}.txt")
    projection = calib.get("P2")
    if projection is None:
        return []
    objects = []
    for obj in parse_kitti_labels(trip_dir / "kitti" / "label_2" / f"{frame_id:06d}.txt"):
        bbox = bbox_from_projected_object(obj, projection, w, h)
        if bbox is None or obj.location[2] <= 0.1:
            continue
        objects.append({"type": obj.object_type, "bbox": bbox, "distance_m": obj.location[2]})
    return objects


def score_trip(trip_dir: Path, pred_path: Path, iou_threshold: float) -> dict[str, float | int | str]:
    doc = load_trip_doc(trip_dir)
    preds = read_predictions(pred_path)
    by_frame: dict[int, list[dict[str, str]]] = {}
    for row in preds:
        by_frame.setdefault(int(row["frame_id"]), []).append(row)
    tp = fp = fn = 0
    distance_errors: list[float] = []
    pred_min_ttc: dict[int, float] = {}
    for frame in doc.get("frames", []):
        frame_id = int(frame.get("frame_id", 0))
        frame_preds = [
            row for row in by_frame.get(frame_id, [])
            if row.get("object_type") and row.get("bbox_x1") not in ("", None)
        ]
        finite_ttc = [
            safe_float(row.get("ttc_s"), math.inf)
            for row in frame_preds
            if safe_float(row.get("ttc_s"), math.inf) != math.inf
        ]
        pred_min_ttc[frame_id] = min(finite_ttc) if finite_ttc else math.inf
        used: set[int] = set()
        for pred in frame_preds:
            pred_box = tuple(float(pred[key]) for key in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"))
            best_idx = -1
            best_iou = 0.0
            gt = gt_objects(trip_dir, frame_id)
            for idx, obj in enumerate(gt):
                if idx in used or obj["type"] != pred["object_type"]:
                    continue
                score = iou(pred_box, obj["bbox"])
                if score > best_iou:
                    best_iou = score
                    best_idx = idx
            if best_iou >= iou_threshold and best_idx >= 0:
                tp += 1
                used.add(best_idx)
                dist = safe_float(pred.get("distance_m"))
                if math.isfinite(dist):
                    distance_errors.append(abs(dist - float(gt[best_idx]["distance_m"])))
            else:
                fp += 1
        fn += max(0, len(gt_objects(trip_dir, frame_id)) - len(used))

    gt_ttc = {
        int(frame.get("frame_id", 0)): safe_float(frame.get("min_ttc"), math.inf)
        for frame in doc.get("frames", [])
    }
    critical_errors = [
        abs(pred_min_ttc[frame_id] - true)
        for frame_id, true in gt_ttc.items()
        if math.isfinite(true) and true < 3.0 and math.isfinite(pred_min_ttc.get(frame_id, math.inf))
    ]
    gt_risk = {fid for fid, val in gt_ttc.items() if math.isfinite(val) and val < 2.0}
    pred_risk = {fid for fid, val in pred_min_ttc.items() if math.isfinite(val) and val < 2.0}
    ttc_tp = len(gt_risk & pred_risk)
    ttc_fp = len(pred_risk - gt_risk)
    ttc_fn = len(gt_risk - pred_risk)
    precision = ttc_tp / max(1, ttc_tp + ttc_fp)
    recall = ttc_tp / max(1, ttc_tp + ttc_fn)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    return {
        "trip_id": trip_dir.name,
        "prediction_file": str(pred_path),
        "det_tp": tp,
        "det_fp": fp,
        "det_fn": fn,
        "det_precision": round(tp / max(1, tp + fp), 4),
        "det_recall": round(tp / max(1, tp + fn), 4),
        "distance_mae_m": round(float(np.mean(distance_errors)), 4) if distance_errors else math.nan,
        "distance_eval_count": len(distance_errors),
        "ttc_mae_critical_s": round(float(np.mean(critical_errors)), 4) if critical_errors else math.nan,
        "ttc_f1_lt2s": round(f1, 4),
    }


def main() -> None:
    args = parse_args()
    requested = set(args.trip or [])
    summaries = []
    dataset = args.dataset_root if args.dataset_root is not None else "practice"
    for trip_dir in discover_trips(dataset):
        if requested and trip_dir.name not in requested:
            continue
        pred_path = args.pred_dir / f"{trip_dir.name}_roadface.csv"
        if not pred_path.exists():
            print(f"Skip {trip_dir.name}: missing {pred_path}")
            continue
        summary = score_trip(trip_dir, pred_path, args.iou_threshold)
        summaries.append(summary)
        print(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"Wrote {args.output.resolve()}")


if __name__ == "__main__":
    main()
