from __future__ import annotations

import unittest
from types import SimpleNamespace

import cv2
import numpy as np
from fleetiq_roadface.birdseye import (
    _perspective_matrices,
    detect_birdseye_lane,
)


def tracker_args() -> SimpleNamespace:
    return SimpleNamespace(
        perspective_top_y_ratio=0.60,
        perspective_bottom_y_ratio=0.995,
        perspective_top_half_width_ratio=0.15,
        perspective_bottom_margin_ratio=0.16,
        bird_destination_margin_ratio=0.22,
        bird_offset_y_ratio=0.94,
        bird_width_tolerance=0.34,
        max_width_std_ratio=0.14,
        max_parallel_slope_delta=0.32,
        histogram_top_ratio=0.18,
        histogram_bottom_ratio=0.98,
        histogram_bands=6,
        histogram_smooth_px=9,
        histogram_peak_distance_ratio=0.08,
        sliding_windows=10,
        window_margin_ratio=0.075,
        window_min_pixels=12,
        previous_fit_margin_ratio=0.065,
        min_lane_pixels=60,
        fit_residual_px=18.0,
        temporal_alpha=0.62,
        lane_width_m=3.7,
    )


def camera_mask_from_bird(
    left: bool = True,
    right: bool = True,
    bottom_missing: bool = False,
    distractor_x: int | None = None,
) -> np.ndarray:
    args = tracker_args()
    h, w = 360, 640
    _matrix, inverse, _src, dst = _perspective_matrices((h, w), args)
    bird = np.zeros((h, w), dtype=np.uint8)
    y_end = 286 if bottom_missing else h - 1
    segments = [(12, 98), (121, 208), (230, y_end)]

    def curve(base_x: float) -> np.ndarray:
        ys = np.arange(0, h, dtype=np.float32)
        xs = base_x + 0.00034 * np.square(ys - h / 2.0)
        return np.stack([xs, ys], axis=1).astype(np.int32)

    left_curve = curve(float(dst[0, 0]))
    right_curve = curve(float(dst[3, 0]))
    for y1, y2 in segments:
        if y2 <= y1:
            continue
        if left:
            cv2.polylines(bird, [left_curve[y1:y2]], False, 255, 8, cv2.LINE_AA)
        if right:
            cv2.polylines(bird, [right_curve[y1:y2]], False, 255, 8, cv2.LINE_AA)
    if distractor_x is not None:
        cv2.line(bird, (distractor_x, 30), (distractor_x, h - 1), 255, 12, cv2.LINE_AA)
    return cv2.warpPerspective(bird, inverse, (w, h), flags=cv2.INTER_NEAREST)


class BirdEyeLaneTrackerTests(unittest.TestCase):
    def test_connects_fragments_when_bottom_is_missing(self) -> None:
        mask = camera_mask_from_bird(bottom_missing=True)
        result = detect_birdseye_lane(mask, None, tracker_args())
        self.assertIsNotNone(result)
        assert result is not None
        self.assertLess(abs(result.offset_m), 0.25)
        self.assertGreater(result.left_pixels[0].size, 100)
        self.assertGreater(result.right_pixels[0].size, 100)

    def test_infers_missing_side_with_the_same_curvature(self) -> None:
        mask = camera_mask_from_bird(left=True, right=False, bottom_missing=True)
        result = detect_birdseye_lane(mask, None, tracker_args())
        self.assertIsNotNone(result)
        assert result is not None
        sample_y = np.linspace(20, 340, 16)
        widths = np.polyval(result.right_fit, sample_y) - np.polyval(
            result.left_fit, sample_y
        )
        self.assertLess(float(np.std(widths)), 1.0)
        self.assertIn("infer_right", result.status)
        self.assertLess(abs(result.offset_m), 0.25)

    def test_rejects_dense_curb_when_it_moves_lane_away_from_ego(self) -> None:
        mask = camera_mask_from_bird(left=True, right=False, distractor_x=625)
        result = detect_birdseye_lane(mask, None, tracker_args())
        self.assertIsNotNone(result)
        assert result is not None
        self.assertLess(abs(result.offset_m), 0.75)
        self.assertTrue(
            "repair_from_left" in result.status or "infer_right" in result.status,
            result.status,
        )


if __name__ == "__main__":
    unittest.main()
