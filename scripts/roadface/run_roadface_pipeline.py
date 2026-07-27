from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np

from scripts.roadface.roadface_lib import (
    COCO_TO_KITTI,
    Detection,
    PRACTICE_ROOT,
    REDACTED_ROOT,
    SimpleTracker,
    attach_distances,
    build_lane_corridor_masks,
    compute_road_and_lane,
    detections_from_labels,
    discover_trips,
    draw_overlay,
    estimate_plane_lane,
    filter_detections_by_lane_corridor,
    find_image,
    finite_or_none,
    load_gt_depth,
    load_trip_doc,
    parse_calibration,
    read_image,
    stereo_depth,
    valid_bbox,
)


class YoloDetector:
    def __init__(self, weights: str, conf: float) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install optional roadface deps first: uv sync --extra roadface") from exc
        self.model = YOLO(weights)
        self.conf = conf

    def __call__(self, image: np.ndarray) -> list[Detection]:
        results = self.model.predict(image, conf=self.conf, verbose=False)
        detections: list[Detection] = []
        if not results:
            return detections
        names = results[0].names
        for box in results[0].boxes:
            cls_name = str(names[int(box.cls[0])]).lower()
            object_type = COCO_TO_KITTI.get(cls_name)
            if object_type is None:
                continue
            bbox = tuple(float(v) for v in box.xyxy[0].tolist())
            valid = valid_bbox(bbox, image.shape[1], image.shape[0])
            if valid is None:
                continue
            detections.append(
                Detection(
                    object_type=object_type,
                    bbox=valid,
                    confidence=float(box.conf[0]),
                    source="yolo",
                )
            )
        return detections


class TransformersDepth:
    def __init__(self, model_id: str) -> None:
        try:
            import torch
            from PIL import Image
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError("Install optional roadface deps first: uv sync --extra roadface") from exc
        device = 0 if torch.cuda.is_available() else -1
        self.pipe = pipeline("depth-estimation", model=model_id, device=device)
        self.image_cls = Image

    def __call__(self, image_bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        result = self.pipe(self.image_cls.fromarray(rgb))
        pred = result.get("predicted_depth")
        if hasattr(pred, "detach"):
            depth = pred.detach().cpu().numpy()
        else:
            depth = np.asarray(pred)
        depth = np.squeeze(depth).astype(np.float32)
        if depth.shape[:2] != image_bgr.shape[:2]:
            depth = cv2.resize(depth, (image_bgr.shape[1], image_bgr.shape[0]), interpolation=cv2.INTER_CUBIC)
        return depth


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run road-facing detection, depth, lane, tracking, relative speed, and TTC."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--dataset-root", type=Path, help="Override dataset root containing trip folders.")
    parser.add_argument("--trip", action="append", help="Trip id. Repeat or omit for all trips in dataset.")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument(
        "--detector",
        choices=("labels", "labels_custom", "yolo", "none"),
        default="labels",
    )
    parser.add_argument("--custom-label-dir-name", default="label2_custom")
    parser.add_argument("--yolo-weights", default="yolo11x.pt")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument(
        "--depth-source",
        default="gt",
        help="gt, stereo, none, or transformers:<huggingface_model_id>.",
    )
    parser.add_argument("--depth-policy", choices=("previous", "nearest"), default="previous")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/roadface/predictions"))
    parser.add_argument("--visualize", choices=("none", "frame", "video", "window"), default="none")
    parser.add_argument("--render-every", type=int, default=1)
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--prefer-label3d", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--lane-method", choices=("classical", "plane"), default="classical")
    parser.add_argument("--lane-filter", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--lane-margin-m", type=float, default=0.25)
    return parser.parse_args()


def dataset_key_or_root(args: argparse.Namespace) -> str:
    if args.dataset_root is not None:
        return str(args.dataset_root)
    return args.dataset


def make_detector(args: argparse.Namespace):
    if args.detector == "yolo":
        return YoloDetector(args.yolo_weights, args.conf)
    return None


def make_depth_model(depth_source: str):
    if depth_source.startswith("transformers:"):
        return TransformersDepth(depth_source.split(":", 1)[1])
    return None


def get_depth(
    depth_source: str,
    depth_model: Any,
    trip_dir: Path,
    frame_id: int,
    left: np.ndarray,
    right: np.ndarray | None,
    calibration: dict[str, np.ndarray],
    depth_policy: str,
) -> tuple[np.ndarray | None, str]:
    if depth_source == "gt":
        return load_gt_depth(trip_dir, frame_id, depth_policy), "gt_depth"
    if depth_source == "stereo":
        return stereo_depth(left, right, calibration) if right is not None else None, "stereo_sgbm"
    if depth_source.startswith("transformers:"):
        return depth_model(left), depth_source
    return None, "none"


def rows_for_frame(
    trip_id: str,
    frame: dict[str, Any],
    detections: list[Detection],
    lane_offset_m: float,
    depth_source_name: str,
) -> list[dict[str, Any]]:
    timestamp = float(frame.get("timestamp", 0.0))
    frame_id = int(frame.get("frame_id", 0))
    if not detections:
        return [
            {
                "trip_id": trip_id,
                "frame_id": frame_id,
                "timestamp": round(timestamp, 4),
                "object_count": 0,
                "track_id": "",
                "object_type": "",
                "confidence": "",
                "bbox_x1": "",
                "bbox_y1": "",
                "bbox_x2": "",
                "bbox_y2": "",
                "x_m": "",
                "z_m": "",
                "distance_m": "",
                "relative_speed_mps": "",
                "ttc_s": "inf",
                "lane_offset_m": finite_or_none(lane_offset_m),
                "detector_source": "",
                "distance_source": depth_source_name,
            }
        ]
    rows: list[dict[str, Any]] = []
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        rows.append(
            {
                "trip_id": trip_id,
                "frame_id": frame_id,
                "timestamp": round(timestamp, 4),
                "object_count": len(detections),
                "track_id": det.track_id,
                "object_type": det.object_type,
                "confidence": round(det.confidence, 4),
                "bbox_x1": round(x1, 2),
                "bbox_y1": round(y1, 2),
                "bbox_x2": round(x2, 2),
                "bbox_y2": round(y2, 2),
                "x_m": finite_or_none(det.lateral_m),
                "z_m": finite_or_none(det.distance_m),
                "distance_m": finite_or_none(det.distance_m),
                "relative_speed_mps": finite_or_none(det.relative_speed_mps),
                "ttc_s": finite_or_none(det.ttc_s),
                "lane_offset_m": finite_or_none(lane_offset_m),
                "detector_source": det.source,
                "distance_source": det.distance_source or depth_source_name,
            }
        )
    return rows


def run_trip(trip_dir: Path, args: argparse.Namespace, detector: Any, depth_model: Any) -> None:
    doc = load_trip_doc(trip_dir)
    frames = doc.get("frames", [])
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{trip_dir.name}_roadface.csv"
    jsonl_path = output_dir / f"{trip_dir.name}_roadface.jsonl"
    video_writer = None
    tracker = SimpleTracker()
    fieldnames = [
        "trip_id", "frame_id", "timestamp", "object_count", "track_id", "object_type",
        "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "x_m", "z_m",
        "distance_m", "relative_speed_mps", "ttc_s", "lane_offset_m",
        "detector_source", "distance_source",
    ]
    start = max(0, args.start)
    end = min(len(frames) - 1, args.end if args.end is not None else len(frames) - 1)
    processed = 0
    with csv_path.open("w", newline="", encoding="utf-8") as csv_handle, jsonl_path.open("w", encoding="utf-8") as jsonl_handle:
        writer = csv.DictWriter(csv_handle, fieldnames=fieldnames)
        writer.writeheader()
        for index in range(start, end + 1, max(1, args.stride)):
            if args.max_frames is not None and processed >= args.max_frames:
                break
            frame = frames[index]
            frame_id = int(frame.get("frame_id", index))
            stem = f"{frame_id:06d}"
            left = read_image(find_image(trip_dir / "kitti" / "image_2", stem))
            if left is None:
                continue
            right = read_image(find_image(trip_dir / "kitti" / "image_3", stem))
            calibration = parse_calibration(trip_dir / "kitti" / "calib" / f"{stem}.txt")
            depth, depth_source_name = get_depth(
                args.depth_source,
                depth_model,
                trip_dir,
                frame_id,
                left,
                right,
                calibration,
                args.depth_policy,
            )
            if args.lane_method == "plane":
                base_road_mask, _, _, _ = compute_road_and_lane(left)
                lane_estimate = estimate_plane_lane(left, depth, calibration, road_mask=base_road_mask)
                road_mask = lane_estimate.road_mask
                lane_mask = lane_estimate.lane_mask
                lane_offset_m = lane_estimate.lane_offset_m
                line_segments = []
                corridor_mask = lane_estimate.corridor_mask
                vertical_corridor_mask = lane_estimate.vertical_corridor_mask
            else:
                road_mask, lane_mask, lane_offset_m, line_segments = compute_road_and_lane(left)
                corridor_mask, vertical_corridor_mask = build_lane_corridor_masks(left.shape, line_segments)
            if args.detector in ("labels", "labels_custom"):
                label_dir_name = "label_2" if args.detector == "labels" else args.custom_label_dir_name
                detections = detections_from_labels(
                    trip_dir / "kitti" / label_dir_name / f"{stem}.txt",
                    calibration,
                    left.shape,
                    source="kitti_label" if args.detector == "labels" else "locateanything_label",
                )
            elif args.detector == "yolo":
                detections = detector(left)
            else:
                detections = []
            attach_distances(detections, depth, calibration, args.prefer_label3d)
            if args.lane_filter:
                detections = filter_detections_by_lane_corridor(
                    detections,
                    corridor_mask,
                    vertical_corridor_mask,
                    lateral_margin_m=args.lane_margin_m,
                )
            timestamp = float(frame.get("timestamp", index / args.fps))
            detections = tracker.update(detections, timestamp)
            frame_rows = rows_for_frame(trip_dir.name, frame, detections, lane_offset_m, depth_source_name)
            writer.writerows(frame_rows)
            jsonl_handle.write(json.dumps({"frame": frame_rows[0], "objects": frame_rows if detections else []}) + "\n")
            if args.visualize != "none" and processed % max(1, args.render_every) == 0:
                vis = draw_overlay(
                    left,
                    detections,
                    road_mask,
                    lane_mask,
                    lane_offset_m,
                    line_segments,
                    corridor_mask,
                    vertical_corridor_mask,
                )
                if args.visualize == "frame":
                    out = output_dir / f"{trip_dir.name}_{frame_id:06d}_roadface.png"
                    cv2.imwrite(str(out), vis)
                elif args.visualize == "window":
                    cv2.imshow("FleetIQ roadface", vis)
                    if (cv2.waitKey(max(1, int(1000 / args.fps))) & 0xFF) in (27, ord("q")):
                        break
                elif args.visualize == "video":
                    if video_writer is None:
                        h, w = vis.shape[:2]
                        video_path = output_dir / f"{trip_dir.name}_roadface.mp4"
                        video_writer = cv2.VideoWriter(
                            str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (w, h)
                        )
                    video_writer.write(vis)
            processed += 1
            if processed == 1 or processed % 100 == 0:
                print(f"{trip_dir.name}: processed {processed} frames")
    if video_writer is not None:
        video_writer.release()
    cv2.destroyAllWindows()
    print(f"Wrote {csv_path}")
    print(f"Wrote {jsonl_path}")


def main() -> None:
    args = parse_args()
    detector = make_detector(args)
    depth_model = make_depth_model(args.depth_source)
    available = discover_trips(dataset_key_or_root(args))
    requested = set(args.trip or [])
    trips = [trip for trip in available if not requested or trip.name in requested]
    if not trips:
        choices = ", ".join(trip.name for trip in available)
        raise SystemExit(f"No trips selected. Available: {choices}")
    if args.depth_source.startswith("transformers:") and args.detector in ("labels", "labels_custom"):
        print("Using label detections plus transformer depth; for redacted trips use --detector yolo.")
    for trip in trips:
        run_trip(trip, args, detector, depth_model)


if __name__ == "__main__":
    main()
