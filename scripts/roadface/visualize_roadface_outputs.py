from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2

from scripts.roadface.roadface_lib import (
    Detection,
    build_lane_corridor_masks,
    compute_road_and_lane,
    discover_trips,
    draw_overlay,
    find_image,
    read_image,
    resolve_trip,
    safe_float,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render road-facing overlays from pipeline CSV outputs.")
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", required=True)
    parser.add_argument("--pred-csv", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=("frame", "video", "window"), default="video")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--fps", type=float, default=20.0)
    return parser.parse_args()


def load_rows(path: Path) -> dict[int, list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(int(row["frame_id"]), []).append(row)
    return grouped


def detections_from_rows(rows: list[dict[str, str]]) -> list[Detection]:
    detections: list[Detection] = []
    for row in rows:
        if not row.get("object_type") or not row.get("bbox_x1"):
            continue
        det = Detection(
            object_type=row["object_type"],
            bbox=tuple(float(row[key]) for key in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2")),
            confidence=safe_float(row.get("confidence"), 0.0),
            source=row.get("detector_source", "csv"),
        )
        det.track_id = int(row["track_id"]) if row.get("track_id") else None
        det.distance_m = safe_float(row.get("distance_m"))
        det.relative_speed_mps = safe_float(row.get("relative_speed_mps"))
        det.ttc_s = safe_float(row.get("ttc_s"), math.inf)
        detections.append(det)
    return detections


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    pred_csv = args.pred_csv or Path("artifacts/roadface/predictions") / f"{trip_dir.name}_roadface.csv"
    grouped = load_rows(pred_csv)
    frame_ids = sorted(grouped)
    if not frame_ids:
        raise SystemExit(f"No rows in {pred_csv}")
    start = max(args.start, frame_ids[0])
    end = args.end if args.end is not None else frame_ids[-1]
    writer = None
    output = args.output or Path("artifacts/roadface/predictions") / f"{trip_dir.name}_overlay.mp4"
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for frame_id in [fid for fid in frame_ids if start <= fid <= end]:
            image = read_image(find_image(trip_dir / "kitti" / "image_2", f"{frame_id:06d}"))
            if image is None:
                continue
            detections = detections_from_rows(grouped[frame_id])
            road_mask, lane_mask, lane_offset_m, line_segments = compute_road_and_lane(image)
            corridor_mask, vertical_corridor_mask = build_lane_corridor_masks(image.shape, line_segments)
            vis = draw_overlay(
                image,
                detections,
                road_mask,
                lane_mask,
                lane_offset_m,
                line_segments,
                corridor_mask,
                vertical_corridor_mask,
            )
            if args.mode == "frame":
                frame_path = output.with_suffix(".png")
                cv2.imwrite(str(frame_path), vis)
                print(f"Wrote {frame_path}")
                break
            if args.mode == "window":
                cv2.imshow("FleetIQ roadface overlay", vis)
                if (cv2.waitKey(max(1, int(1000 / args.fps))) & 0xFF) in (27, ord("q")):
                    break
            else:
                if writer is None:
                    h, w = vis.shape[:2]
                    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (w, h))
                writer.write(vis)
    finally:
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()
    if args.mode == "video":
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
