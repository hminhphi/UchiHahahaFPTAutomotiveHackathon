from __future__ import annotations

import math
from inspect import signature
from pathlib import Path

import cv2
import numpy as np
import pytest
from fleetiq_data import Calibration
from fleetiq_data.trips import TripRecord
from fleetiq_roadface.cli import parse_args
from fleetiq_roadface.depth import (
    bbox_depth,
    load_ground_truth_depth,
    stereo_depth,
)


def calibration(fx: float = 80.0, baseline_m: float = 0.2) -> Calibration:
    p2 = np.array(
        [[fx, 0.0, 80.0, 0.0], [0.0, fx, 40.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
        dtype=np.float64,
    )
    p3 = p2.copy()
    p3[0, 3] = -fx * baseline_m
    return Calibration(
        values={"P2": p2, "P3": p3},
        projections={"P2": p2, "P3": p3},
        fx=fx,
        fy=fx,
        cx=80.0,
        cy=40.0,
        baseline_m=baseline_m,
    )


def test_ground_truth_previous_depth_never_uses_a_future_frame(tmp_path: Path) -> None:
    trip = TripRecord(dataset_root=tmp_path, trip_id="T01")
    trip.depth_dir.mkdir(parents=True)
    np.save(trip.depth_dir / "000005.npy", np.full((4, 4), 5.0, dtype=np.float32))

    assert load_ground_truth_depth(trip, frame_index=3) is None

    np.save(trip.depth_dir / "000000.npy", np.full((4, 4), 3.0, dtype=np.float32))
    depth = load_ground_truth_depth(trip, frame_index=3)
    assert depth is not None
    assert np.all(depth == 3.0)


def test_stereo_depth_uses_explicit_calibration_on_shifted_grayscale() -> None:
    rng = np.random.default_rng(7)
    left = rng.integers(0, 256, size=(80, 160), dtype=np.uint8)
    left = cv2.GaussianBlur(left, (3, 3), 0)
    disparity_px = 8
    right = np.zeros_like(left)
    right[:, :-disparity_px] = left[:, disparity_px:]

    depth = stereo_depth(
        left,
        right,
        calibration(),
        num_disparities=16,
        block_size=5,
        max_depth_m=20.0,
    )

    valid = depth[np.isfinite(depth)]
    assert valid.size > depth.size * 0.45
    assert math.isclose(float(np.median(valid)), 2.0, rel_tol=0.20)


def test_bbox_depth_returns_json_safe_missing_value() -> None:
    depth = np.full((10, 10), np.nan, dtype=np.float32)
    assert bbox_depth(depth, (1.0, 1.0, 8.0, 8.0)) is None


def test_runtime_depth_api_exposes_only_causal_previous_lookup() -> None:
    assert tuple(signature(load_ground_truth_depth).parameters) == (
        "trip",
        "frame_index",
    )
    with pytest.raises(SystemExit):
        parse_args(["--depth-policy", "nearest"])
