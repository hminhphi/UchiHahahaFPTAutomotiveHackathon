"""Command-line entry point for local road-facing inference."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from fleetiq_data import DatasetPaths, discover_trips

from .pipeline import PipelineOptions, RoadfacePipeline

DEFAULT_DATASET_ROOTS = {
    "practice": Path("data/Practice_Dataset/Practice_Dataset"),
    "redacted": Path("data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted"),
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FleetIQ road-facing detection, depth, lane, tracking, and TTC."
    )
    parser.add_argument(
        "--dataset",
        choices=("practice", "redacted"),
        default="practice",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Explicit root containing organizer trip folders.",
    )
    parser.add_argument(
        "--trip", action="append", help="Trip ID; repeat for multiple trips."
    )
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument(
        "--detector",
        choices=("labels", "labels_custom", "none"),
        default="labels",
    )
    parser.add_argument("--custom-label-dir-name", default="label2_custom")
    parser.add_argument(
        "--depth-source",
        choices=("gt", "stereo", "none"),
        default="gt",
    )
    parser.add_argument(
        "--depth-policy",
        choices=("previous", "nearest", "exact"),
        default="previous",
    )
    parser.add_argument(
        "--lane-method",
        choices=("classical", "plane"),
        default="classical",
    )
    parser.add_argument(
        "--lane-filter",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--lane-margin-m", type=float, default=0.25)
    parser.add_argument(
        "--prefer-label3d",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/predictions/roadface"),
    )
    parser.add_argument("--visualize", action="store_true")
    parser.add_argument("--fps", type=float, default=20.0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    dataset_root = args.dataset_root or DEFAULT_DATASET_ROOTS[args.dataset]
    if not dataset_root.is_dir():
        print(f"Dataset root does not exist: {dataset_root}")
        return 2
    paths = DatasetPaths(dataset_root)
    available = discover_trips(paths)
    requested = {trip.casefold() for trip in (args.trip or [])}
    selected = [
        trip
        for trip in available
        if not requested or trip.trip_id.casefold() in requested
    ]
    if not selected:
        choices = ", ".join(trip.trip_id for trip in available)
        print(f"No trips selected. Available: {choices}")
        return 2
    pipeline = RoadfacePipeline(
        dataset_paths=paths,
        output_root=args.output_dir,
        detector=None,
        depth_model=None,
    )
    options = PipelineOptions(
        detector_source=args.detector,
        custom_label_dir_name=args.custom_label_dir_name,
        depth_source=args.depth_source,
        depth_policy=args.depth_policy,
        lane_method=args.lane_method,
        lane_filter=args.lane_filter,
        lane_margin_m=args.lane_margin_m,
        prefer_label3d=args.prefer_label3d,
        visualize=args.visualize,
    )
    total = 0
    for trip in selected:
        written = pipeline.run_trip(
            trip,
            start=args.start,
            end=args.end,
            stride=args.stride,
            max_frames=args.max_frames,
            fps=args.fps,
            options=options,
        )
        total += len(written)
        print(f"{trip.trip_id}: wrote {len(written)} frame result(s)")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
