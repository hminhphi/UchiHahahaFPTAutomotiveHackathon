from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from fleetiq_training_roadface.lane_mmae import (
    fuse_estimates,
    geometry_lane_model,
    hough_lane_model,
    load_trip_frame,
    threshold_lane_model,
)
from fleetiq_training_roadface.experimental import resolve_trip


def parse_frame_ids(raw: str) -> list[int]:
    frame_ids: list[int] = []
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_s, end_s = item.split("-", 1)
            frame_ids.extend(range(int(start_s), int(end_s) + 1))
        else:
            frame_ids.append(int(item))
    return sorted(set(frame_ids))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit lane model decisions on selected road-facing frames.")
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", default="T06-Sample")
    parser.add_argument("--frames", default="100,127", help="Comma list and/or ranges, e.g. 100,127,320-330")
    parser.add_argument("--history-sigma-m", type=float, default=0.35)
    parser.add_argument("--output", type=Path, default=Path("artifacts/roadface/lane_demo/lane_model_audit.csv"))
    return parser.parse_args()


def fmt(value: float) -> str:
    return "" if not math.isfinite(value) else f"{value:.4f}"


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    frame_ids = parse_frame_ids(args.frames)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    previous_offset: float | None = None
    rows: list[dict[str, str]] = []
    for frame_id in frame_ids:
        image = load_trip_frame(trip_dir, frame_id)
        model1 = hough_lane_model(image)
        model2 = threshold_lane_model(image)
        model3 = geometry_lane_model(image, trip_dir, frame_id)
        fused = fuse_estimates(model1, model2, model3, previous_offset, args.history_sigma_m, image)
        if math.isfinite(fused.estimate.offset_m):
            previous_offset = fused.estimate.offset_m
        rows.append(
            {
                "trip": trip_dir.name,
                "frame": f"{frame_id:06d}",
                "m1_valid": str(model1.valid),
                "m1_offset_m": fmt(model1.offset_m),
                "m1_conf": f"{model1.confidence:.4f}",
                "m1_note": model1.note,
                "m2_valid": str(model2.valid),
                "m2_offset_m": fmt(model2.offset_m),
                "m2_conf": f"{model2.confidence:.4f}",
                "m2_note": model2.note,
                "m3_valid": str(model3.valid),
                "m3_offset_m": fmt(model3.offset_m),
                "m3_conf": f"{model3.confidence:.4f}",
                "m3_note": model3.note,
                "p_m1": f"{fused.probabilities[0]:.4f}",
                "p_m2": f"{fused.probabilities[1]:.4f}",
                "p_m3": f"{fused.probabilities[2]:.4f}",
                "selected": fused.selected_model,
                "fused_offset_m": fmt(fused.estimate.offset_m),
                "fused_conf": f"{fused.estimate.confidence:.4f}",
            }
        )

    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["trip", "frame"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.output.resolve()} ({len(rows)} frames)")


if __name__ == "__main__":
    main()
