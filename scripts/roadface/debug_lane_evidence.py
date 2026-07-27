from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np

from scripts.roadface.roadface_lib import (
    compute_road_and_lane,
    detections_from_labels,
    detections_ignore_mask,
    estimate_plane_lane,
    find_image,
    lane_marking_evidence_mask,
    load_gt_depth,
    parse_calibration,
    read_image,
    resolve_trip,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render and log every intermediate used by the plane-based lane detector."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", default="T01-Sample")
    parser.add_argument("--frame", type=int, default=300)
    parser.add_argument("--lane-width-m", type=float, default=3.7)
    parser.add_argument("--lookahead-m", type=float, default=10.0)
    parser.add_argument("--output", type=Path, default=Path("artifacts/roadface/lane_evidence_debug.png"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    stem = f"{args.frame:06d}"
    image = read_image(find_image(trip_dir / "kitti" / "image_2", stem))
    if image is None:
        raise FileNotFoundError(stem)
    calibration = parse_calibration(trip_dir / "kitti" / "calib" / f"{stem}.txt")
    depth = load_gt_depth(trip_dir, args.frame, "nearest")
    road_mask, _, _, _ = compute_road_and_lane(image)
    detections = detections_from_labels(
        trip_dir / "kitti" / "label_2" / f"{stem}.txt", calibration, image.shape
    )
    ignore_mask = detections_ignore_mask(image.shape, detections) if detections else None
    evidence = lane_marking_evidence_mask(image, road_mask, ignore_mask)
    estimate = estimate_plane_lane(
        image,
        depth,
        calibration,
        road_mask=road_mask,
        ignore_mask=ignore_mask,
        lane_width_m=args.lane_width_m,
        lookahead_m=args.lookahead_m,
    )
    overlay = image.copy()
    color = np.zeros_like(image)
    color[:, :, 2] = 255
    color[:, :, 1] = 210
    overlay = np.where(evidence[:, :, None] > 0, cv2.addWeighted(overlay, 0.45, color, 0.55, 0), overlay)
    projected = image.copy()
    projected[estimate.corridor_mask > 0] = cv2.addWeighted(
        projected, 0.70, np.full_like(projected, (220, 180, 0)), 0.30, 0
    )[estimate.corridor_mask > 0]
    projected[estimate.lane_mask > 0] = (0, 210, 255)
    ignore_view = cv2.cvtColor(ignore_mask, cv2.COLOR_GRAY2BGR) if ignore_mask is not None else np.zeros_like(image)
    side = np.vstack([
        np.hstack([image, cv2.cvtColor(road_mask, cv2.COLOR_GRAY2BGR), cv2.cvtColor(evidence, cv2.COLOR_GRAY2BGR)]),
        np.hstack([overlay, projected, ignore_view]),
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), side)
    print(f"Wrote {args.output.resolve()}")
    print(f"trip={trip_dir.name} frame={stem} image={image.shape[1]}x{image.shape[0]}")
    print(f"road_pixels={int(np.count_nonzero(road_mask))} evidence_pixels={int(np.count_nonzero(evidence))}")
    print(f"ignored_object_pixels={0 if ignore_mask is None else int(np.count_nonzero(ignore_mask))} labels={len(detections)}")
    print(
        "plane="
        f"{estimate.plane.source} normal={estimate.plane.normal.tolist()} d={estimate.plane.d:.4f} "
        f"inliers={estimate.plane.inlier_count} ratio={estimate.plane.inlier_ratio:.3f}"
    )
    print(
        f"lane_width_m={args.lane_width_m:.2f} lookahead_m={args.lookahead_m:.1f} "
        f"offset_m={estimate.lane_offset_m:+.3f} heading_deg={estimate.heading_deg:+.3f} confidence={estimate.confidence:.3f}"
    )
    print(f"fit={estimate.note}")


if __name__ == "__main__":
    main()
