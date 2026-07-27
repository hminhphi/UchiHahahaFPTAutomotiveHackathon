from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class BirdEyeLaneResult:
    left_fit: np.ndarray
    right_fit: np.ndarray
    center_fit: np.ndarray
    left_pixels: tuple[np.ndarray, np.ndarray]
    right_pixels: tuple[np.ndarray, np.ndarray]
    left_curve_image: list[tuple[float, float]]
    right_curve_image: list[tuple[float, float]]
    center_curve_image: list[tuple[float, float]]
    left_coeff_image: np.ndarray
    right_coeff_image: np.ndarray
    center_coeff_image: np.ndarray
    lane_width_px: float
    lane_center_x_px: float
    ego_center_x_px: float
    offset_px: float
    offset_m: float
    heading_deg: float
    confidence: float
    anchor_y_image: float
    status: str
    bird_mask: np.ndarray
    source_points: np.ndarray
    destination_points: np.ndarray


@dataclass
class _Candidate:
    left_fit: np.ndarray | None
    right_fit: np.ndarray | None
    left_pixels: tuple[np.ndarray, np.ndarray]
    right_pixels: tuple[np.ndarray, np.ndarray]
    status: str
    confidence_scale: float = 1.0


class BirdEyeLaneTracker:
    """CarND-style lane tracker operating on an AI lane-line mask."""

    def __init__(self) -> None:
        self.left_fit: np.ndarray | None = None
        self.right_fit: np.ndarray | None = None
        self.failures = 0

    def reset(self) -> None:
        self.left_fit = None
        self.right_fit = None
        self.failures = 0

    @property
    def has_previous(self) -> bool:
        return self.left_fit is not None and self.right_fit is not None

    def previous(self) -> tuple[np.ndarray | None, np.ndarray | None]:
        return self.left_fit, self.right_fit

    def update(self, left_fit: np.ndarray, right_fit: np.ndarray) -> None:
        self.left_fit = left_fit.astype(np.float64)
        self.right_fit = right_fit.astype(np.float64)
        self.failures = 0

    def mark_failure(self) -> None:
        self.failures += 1
        if self.failures >= 6:
            self.reset()


def _perspective_matrices(
    shape_hw: tuple[int, int],
    args: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    h, w = shape_hw
    top_y = float(np.clip(args.perspective_top_y_ratio, 0.35, 0.85) * (h - 1))
    bottom_y = float(np.clip(args.perspective_bottom_y_ratio, 0.80, 1.0) * (h - 1))
    top_half = float(np.clip(args.perspective_top_half_width_ratio, 0.03, 0.45) * w)
    bottom_margin = float(np.clip(args.perspective_bottom_margin_ratio, 0.0, 0.42) * w)
    destination_margin = float(np.clip(args.bird_destination_margin_ratio, 0.05, 0.42) * w)

    src = np.float32(
        [
            [bottom_margin, bottom_y],
            [w / 2.0 - top_half, top_y],
            [w / 2.0 + top_half, top_y],
            [w - 1.0 - bottom_margin, bottom_y],
        ]
    )
    dst = np.float32(
        [
            [destination_margin, h - 1.0],
            [destination_margin, 0.0],
            [w - 1.0 - destination_margin, 0.0],
            [w - 1.0 - destination_margin, h - 1.0],
        ]
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    inverse = cv2.getPerspectiveTransform(dst, src)
    return matrix, inverse, src, dst


def _warp_binary(mask: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    h, w = mask.shape[:2]
    warped = cv2.warpPerspective(mask, matrix, (w, h), flags=cv2.INTER_NEAREST)
    return np.where(warped > 0, 255, 0).astype(np.uint8)


def _smooth_histogram(histogram: np.ndarray, radius: int) -> np.ndarray:
    radius = max(1, int(radius))
    kernel_size = radius * 2 + 1
    kernel = np.ones(kernel_size, dtype=np.float64) / kernel_size
    return np.convolve(histogram.astype(np.float64), kernel, mode="same")


def _multi_band_histogram(mask: np.ndarray, args: Any) -> np.ndarray:
    h, _w = mask.shape[:2]
    top = int(np.clip(args.histogram_top_ratio, 0.0, 0.9) * h)
    bottom = int(np.clip(args.histogram_bottom_ratio, 0.1, 1.0) * h)
    if bottom <= top:
        top, bottom = h // 3, h
    bands = max(2, int(args.histogram_bands))
    edges = np.linspace(top, bottom, bands + 1, dtype=np.int32)
    histogram = np.zeros(mask.shape[1], dtype=np.float64)
    used = 0
    for index in range(bands):
        y1, y2 = int(edges[index]), int(edges[index + 1])
        band = mask[y1:y2] > 0
        if y2 <= y1 or np.count_nonzero(band) < 4:
            continue
        profile = band.mean(axis=0)
        peak = float(profile.max())
        if peak <= 0:
            continue
        # Equalized bands prevent a dense bottom fragment from dominating all seeds.
        histogram += profile / peak
        used += 1
    if used == 0:
        histogram = np.sum(mask > 0, axis=0).astype(np.float64)
    return _smooth_histogram(histogram, int(args.histogram_smooth_px))


def _local_peaks(histogram: np.ndarray, min_distance: int, max_count: int = 16) -> list[int]:
    if histogram.size < 3 or float(histogram.max()) <= 0:
        return []
    candidates = np.where(
        (histogram[1:-1] >= histogram[:-2])
        & (histogram[1:-1] >= histogram[2:])
        & (histogram[1:-1] >= 0.12 * histogram.max())
    )[0] + 1
    ordered = sorted((int(x) for x in candidates), key=lambda x: float(histogram[x]), reverse=True)
    selected: list[int] = []
    for x in ordered:
        if all(abs(x - other) >= min_distance for other in selected):
            selected.append(x)
        if len(selected) >= max_count:
            break
    return selected


def _seed_pair(
    mask: np.ndarray,
    ego_x: float,
    expected_width: float,
    args: Any,
) -> tuple[float | None, float | None, str]:
    histogram = _multi_band_histogram(mask, args)
    peaks = _local_peaks(
        histogram,
        min_distance=max(8, int(args.histogram_peak_distance_ratio * mask.shape[1])),
    )
    min_width = expected_width * (1.0 - args.bird_width_tolerance)
    max_width = expected_width * (1.0 + args.bird_width_tolerance)
    candidates: list[tuple[float, float, float]] = []
    for left_index in range(len(peaks) - 1):
        for right_index in range(left_index + 1, len(peaks)):
            left, right = sorted((float(peaks[left_index]), float(peaks[right_index])))
            width = right - left
            if not (min_width <= width <= max_width):
                continue
            center = (left + right) / 2.0
            center_cost = abs(center - ego_x) / max(expected_width, 1.0)
            width_cost = abs(width - expected_width) / max(expected_width, 1.0)
            strength = float(histogram[int(left)] + histogram[int(right)])
            candidates.append((center_cost + 0.55 * width_cost - 0.025 * strength, left, right))
    if candidates:
        _cost, left, right = min(candidates, key=lambda item: item[0])
        return left, right, "histogram_pair"

    left_peaks = [float(x) for x in peaks if x < ego_x]
    right_peaks = [float(x) for x in peaks if x > ego_x]
    if left_peaks:
        left = min(left_peaks, key=lambda x: abs(x - (ego_x - expected_width / 2.0)))
        return left, None, "histogram_left_only"
    if right_peaks:
        right = min(right_peaks, key=lambda x: abs(x - (ego_x + expected_width / 2.0)))
        return None, right, "histogram_right_only"
    return None, None, "histogram_empty"


def _robust_fit(y: np.ndarray, x: np.ndarray, args: Any) -> np.ndarray | None:
    if y.size < max(12, int(args.min_lane_pixels)):
        return None
    keep = np.ones(y.shape[0], dtype=bool)
    fit: np.ndarray | None = None
    for _ in range(4):
        if int(keep.sum()) < max(12, int(args.min_lane_pixels)):
            return None
        fit = np.polyfit(y[keep], x[keep], 2)
        residual = np.abs(x - np.polyval(fit, y))
        median = float(np.median(residual[keep]))
        mad = float(np.median(np.abs(residual[keep] - median)))
        threshold = max(float(args.fit_residual_px), median + 3.5 * max(mad, 1.0))
        next_keep = residual <= threshold
        if np.array_equal(next_keep, keep):
            break
        keep = next_keep
    return None if fit is None else fit.astype(np.float64)


def _pixels_near_fit(
    mask: np.ndarray,
    fit: np.ndarray,
    margin: int,
) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.nonzero(mask)
    if y.size == 0:
        return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32)
    expected_x = np.polyval(fit, y)
    selected = np.abs(x - expected_x) <= margin
    return y[selected].astype(np.int32), x[selected].astype(np.int32)


def _window_pixels(
    mask: np.ndarray,
    seed_x: float,
    args: Any,
) -> tuple[np.ndarray, np.ndarray]:
    h, w = mask.shape[:2]
    y_all, x_all = np.nonzero(mask)
    if y_all.size == 0:
        return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32)
    windows = max(5, int(args.sliding_windows))
    margin = max(8, int(args.window_margin_ratio * w))
    minpix = max(4, int(args.window_min_pixels))
    edges = np.linspace(0, h, windows + 1, dtype=np.int32)

    anchor_scores: list[tuple[int, int, np.ndarray]] = []
    for index in range(windows):
        y1, y2 = int(edges[index]), int(edges[index + 1])
        indices = np.where(
            (y_all >= y1)
            & (y_all < y2)
            & (x_all >= seed_x - margin)
            & (x_all <= seed_x + margin)
        )[0]
        # Slight lower-image preference, without requiring a valid bottom row.
        score = int(indices.size + round(0.08 * index * indices.size))
        anchor_scores.append((score, index, indices))
    score, anchor_index, anchor_indices = max(anchor_scores, key=lambda item: item[0])
    if score <= 0:
        return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32)

    selected_parts: list[np.ndarray] = [anchor_indices]

    def sweep(indices: list[int], center_x: float) -> None:
        previous_centers: list[tuple[float, float]] = []
        for index in indices:
            y1, y2 = int(edges[index]), int(edges[index + 1])
            y_center = (y1 + y2) / 2.0
            predicted_x = center_x
            if len(previous_centers) >= 2:
                (y_a, x_a), (y_b, x_b) = previous_centers[-2:]
                if abs(y_b - y_a) > 1:
                    predicted_x = x_b + (x_b - x_a) * (y_center - y_b) / (y_b - y_a)
            indices_here = np.where(
                (y_all >= y1)
                & (y_all < y2)
                & (x_all >= predicted_x - margin)
                & (x_all <= predicted_x + margin)
            )[0]
            if indices_here.size:
                selected_parts.append(indices_here)
            if indices_here.size >= minpix:
                center_x = float(np.median(x_all[indices_here]))
                previous_centers.append((y_center, center_x))

    anchor_center = float(np.median(x_all[anchor_indices])) if anchor_indices.size else float(seed_x)
    sweep(list(range(anchor_index - 1, -1, -1)), anchor_center)
    sweep(list(range(anchor_index + 1, windows)), anchor_center)
    selected = np.unique(np.concatenate(selected_parts))
    return y_all[selected].astype(np.int32), x_all[selected].astype(np.int32)


def _fit_lane(
    mask: np.ndarray,
    seed_x: float | None,
    previous_fit: np.ndarray | None,
    args: Any,
) -> tuple[np.ndarray | None, tuple[np.ndarray, np.ndarray], str]:
    if previous_fit is not None:
        margin = max(8, int(args.previous_fit_margin_ratio * mask.shape[1]))
        y, x = _pixels_near_fit(mask, previous_fit, margin)
        fit = _robust_fit(y.astype(np.float64), x.astype(np.float64), args)
        if fit is not None:
            return fit, (y, x), "previous_fit"
    if seed_x is None:
        empty = np.empty(0, dtype=np.int32)
        return None, (empty, empty), "no_seed"
    y, x = _window_pixels(mask, seed_x, args)
    fit = _robust_fit(y.astype(np.float64), x.astype(np.float64), args)
    return fit, (y, x), "sliding_window" if fit is not None else "window_fit_failed"


def _fit_quality(
    fit: np.ndarray | None,
    pixels: tuple[np.ndarray, np.ndarray],
) -> float:
    if fit is None or pixels[0].size == 0:
        return 0.0
    y, x = pixels
    residual = np.abs(x - np.polyval(fit, y))
    return float(pixels[0].size / max(1.0, 1.0 + np.median(residual)))


def _normalize_candidate(
    candidate: _Candidate,
    expected_width: float,
    ego_x: float,
    shape_hw: tuple[int, int],
    previous: tuple[np.ndarray | None, np.ndarray | None],
    args: Any,
) -> _Candidate | None:
    h, _w = shape_hw
    left_fit = candidate.left_fit
    right_fit = candidate.right_fit
    left_pixels = candidate.left_pixels
    right_pixels = candidate.right_pixels
    status = candidate.status
    confidence_scale = candidate.confidence_scale

    if left_fit is None and right_fit is None:
        previous_left, previous_right = previous
        if previous_left is None or previous_right is None:
            return None
        return _Candidate(
            previous_left.copy(),
            previous_right.copy(),
            left_pixels,
            right_pixels,
            f"{status}|reuse_previous",
            0.45,
        )
    if left_fit is None:
        left_fit = right_fit.copy()
        left_fit[-1] -= expected_width
        status += "|infer_left"
        confidence_scale *= 0.72
    elif right_fit is None:
        right_fit = left_fit.copy()
        right_fit[-1] += expected_width
        status += "|infer_right"
        confidence_scale *= 0.72

    assert left_fit is not None and right_fit is not None
    sample_y = np.linspace(0.08 * h, 0.98 * h, 24)
    left_x = np.polyval(left_fit, sample_y)
    right_x = np.polyval(right_fit, sample_y)
    widths = right_x - left_x
    width_mean = float(np.mean(widths))
    width_std = float(np.std(widths))
    slope_delta = float(
        np.mean(
            np.abs(
                np.polyval(np.polyder(left_fit), sample_y)
                - np.polyval(np.polyder(right_fit), sample_y)
            )
        )
    )
    y_eval = 0.94 * (h - 1)
    left_near = float(np.polyval(left_fit, y_eval))
    right_near = float(np.polyval(right_fit, y_eval))
    brackets_ego = left_near - 0.12 * expected_width <= ego_x <= right_near + 0.12 * expected_width
    width_valid = (
        np.all(widths > 0)
        and expected_width * (1.0 - args.bird_width_tolerance) <= width_mean
        <= expected_width * (1.0 + args.bird_width_tolerance)
        and width_std <= args.max_width_std_ratio * expected_width
    )
    parallel_valid = slope_delta <= args.max_parallel_slope_delta
    if width_valid and parallel_valid and brackets_ego:
        return _Candidate(
            left_fit,
            right_fit,
            left_pixels,
            right_pixels,
            status,
            confidence_scale,
        )

    left_quality = _fit_quality(left_fit, left_pixels)
    right_quality = _fit_quality(right_fit, right_pixels)
    if max(left_quality, right_quality) > 0:
        left_center = float(np.polyval(left_fit, y_eval) + expected_width / 2.0)
        right_center = float(np.polyval(right_fit, y_eval) - expected_width / 2.0)
        left_position_cost = abs(left_center - ego_x) / max(expected_width, 1.0)
        right_position_cost = abs(right_center - ego_x) / max(expected_width, 1.0)
        left_score = left_quality / (1.0 + 4.0 * left_position_cost)
        right_score = right_quality / (1.0 + 4.0 * right_position_cost)
        if left_score >= right_score:
            right_fit = left_fit.copy()
            right_fit[-1] += expected_width
            status += "|repair_from_left"
        else:
            left_fit = right_fit.copy()
            left_fit[-1] -= expected_width
            status += "|repair_from_right"
        return _Candidate(
            left_fit,
            right_fit,
            left_pixels,
            right_pixels,
            status,
            confidence_scale * 0.60,
        )

    previous_left, previous_right = previous
    if previous_left is not None and previous_right is not None:
        return _Candidate(
            previous_left.copy(),
            previous_right.copy(),
            left_pixels,
            right_pixels,
            f"{status}|reject_reuse_previous",
            0.38,
        )
    return None


def _blend_fit(previous: np.ndarray, current: np.ndarray, alpha: float, h: int) -> np.ndarray:
    alpha = float(np.clip(alpha, 0.0, 1.0))
    sample_y = np.linspace(0, h - 1, 48)
    blended_x = alpha * np.polyval(current, sample_y) + (1.0 - alpha) * np.polyval(previous, sample_y)
    return np.polyfit(sample_y, blended_x, 2).astype(np.float64)


def _project_fit(
    fit: np.ndarray,
    inverse: np.ndarray,
    shape_hw: tuple[int, int],
) -> list[tuple[float, float]]:
    h, w = shape_hw
    bird_y = np.linspace(0, h - 1, 120, dtype=np.float32)
    bird_x = np.polyval(fit, bird_y).astype(np.float32)
    points = np.stack([bird_x, bird_y], axis=1).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(points, inverse).reshape(-1, 2)
    valid = (
        np.isfinite(projected[:, 0])
        & np.isfinite(projected[:, 1])
        & (projected[:, 0] >= -0.15 * w)
        & (projected[:, 0] <= 1.15 * w)
        & (projected[:, 1] >= 0)
        & (projected[:, 1] <= h - 1)
    )
    curve = [(float(x), float(y)) for x, y in projected[valid]]
    return sorted(curve, key=lambda point: point[1])


def _image_coeff(curve: list[tuple[float, float]]) -> np.ndarray:
    if len(curve) < 3:
        return np.zeros(3, dtype=np.float64)
    points = np.asarray(curve, dtype=np.float64)
    return np.polyfit(points[:, 1], points[:, 0], 2).astype(np.float64)


def _project_point(point: tuple[float, float], matrix: np.ndarray) -> tuple[float, float]:
    source = np.asarray(point, dtype=np.float32).reshape(1, 1, 2)
    projected = cv2.perspectiveTransform(source, matrix).reshape(2)
    return float(projected[0]), float(projected[1])


def detect_birdseye_lane(
    lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    args: Any,
    tracker: BirdEyeLaneTracker | None = None,
) -> BirdEyeLaneResult | None:
    h, w = lane_mask.shape[:2]
    matrix, inverse, src, dst = _perspective_matrices((h, w), args)
    bird_mask = _warp_binary(lane_mask, matrix)
    if road_mask is not None and np.count_nonzero(road_mask) > 100:
        bird_road = _warp_binary(road_mask, matrix)
        bird_road = cv2.dilate(
            bird_road,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)),
            iterations=1,
        )
        bird_mask = cv2.bitwise_and(bird_mask, bird_road)
    bird_mask = cv2.morphologyEx(
        bird_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 11)),
        iterations=1,
    )

    ego_x_bird, _ego_y_bird = _project_point((w / 2.0, h - 1.0), matrix)
    expected_width = float(dst[3, 0] - dst[0, 0])
    previous = tracker.previous() if tracker is not None else (None, None)
    left_seed, right_seed, seed_status = _seed_pair(bird_mask, ego_x_bird, expected_width, args)
    left_fit, left_pixels, left_status = _fit_lane(bird_mask, left_seed, previous[0], args)
    right_fit, right_pixels, right_status = _fit_lane(bird_mask, right_seed, previous[1], args)
    candidate = _normalize_candidate(
        _Candidate(
            left_fit,
            right_fit,
            left_pixels,
            right_pixels,
            f"{seed_status}|L:{left_status}|R:{right_status}",
        ),
        expected_width,
        ego_x_bird,
        (h, w),
        previous,
        args,
    )
    if candidate is None:
        if tracker is not None:
            tracker.mark_failure()
        return None

    assert candidate.left_fit is not None and candidate.right_fit is not None
    left_fit = candidate.left_fit
    right_fit = candidate.right_fit
    if tracker is not None and tracker.has_previous and "reuse_previous" not in candidate.status:
        alpha = float(args.temporal_alpha)
        assert previous[0] is not None and previous[1] is not None
        left_fit = _blend_fit(previous[0], left_fit, alpha, h)
        right_fit = _blend_fit(previous[1], right_fit, alpha, h)
        candidate.status += "|temporal"
    if tracker is not None:
        tracker.update(left_fit, right_fit)

    center_fit = (left_fit + right_fit) / 2.0
    y_eval = float(np.clip(args.bird_offset_y_ratio, 0.55, 1.0) * (h - 1))
    left_x = float(np.polyval(left_fit, y_eval))
    right_x = float(np.polyval(right_fit, y_eval))
    center_x = float(np.polyval(center_fit, y_eval))
    lane_width = max(right_x - left_x, 1.0)
    offset_px = ego_x_bird - center_x
    offset_m = offset_px * float(args.lane_width_m) / lane_width
    slope = float(np.polyval(np.polyder(center_fit), y_eval))
    heading_deg = float(math.degrees(math.atan(-slope)))

    left_curve = _project_fit(left_fit, inverse, (h, w))
    right_curve = _project_fit(right_fit, inverse, (h, w))
    center_curve = _project_fit(center_fit, inverse, (h, w))
    left_coeff_image = _image_coeff(left_curve)
    right_coeff_image = _image_coeff(right_curve)
    center_coeff_image = _image_coeff(center_curve)
    anchor_x = float(np.polyval(center_fit, 0.65 * (h - 1)))
    _anchor_x_image, anchor_y_image = _project_point((anchor_x, 0.65 * (h - 1)), inverse)

    total_support = left_pixels[0].size + right_pixels[0].size
    support_score = min(1.0, total_support / max(2.0 * float(args.min_lane_pixels) * 5.0, 1.0))
    sample_y = np.linspace(0.1 * h, 0.98 * h, 24)
    widths = np.polyval(right_fit, sample_y) - np.polyval(left_fit, sample_y)
    width_stability = 1.0 - min(1.0, float(np.std(widths)) / max(0.20 * expected_width, 1.0))
    confidence = float(
        np.clip(
            (0.18 + 0.52 * support_score + 0.30 * width_stability) * candidate.confidence_scale,
            0.05,
            0.98,
        )
    )
    return BirdEyeLaneResult(
        left_fit=left_fit,
        right_fit=right_fit,
        center_fit=center_fit,
        left_pixels=left_pixels,
        right_pixels=right_pixels,
        left_curve_image=left_curve,
        right_curve_image=right_curve,
        center_curve_image=center_curve,
        left_coeff_image=left_coeff_image,
        right_coeff_image=right_coeff_image,
        center_coeff_image=center_coeff_image,
        lane_width_px=lane_width,
        lane_center_x_px=center_x,
        ego_center_x_px=ego_x_bird,
        offset_px=offset_px,
        offset_m=offset_m,
        heading_deg=heading_deg,
        confidence=confidence,
        anchor_y_image=anchor_y_image,
        status=f"birdseye:{candidate.status}",
        bird_mask=bird_mask,
        source_points=src,
        destination_points=dst,
    )
