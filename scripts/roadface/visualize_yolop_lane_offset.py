from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np

from scripts.roadface.carnd_lane_tracker import BirdEyeLaneTracker, detect_birdseye_lane
from scripts.roadface.roadface_lib import (
    CLASS_COLORS,
    detections_from_labels,
    draw_tag,
    find_image,
    parse_calibration,
    read_image,
    resolve_trip,
)


@dataclass(frozen=True)
class LaneOffsetEstimate:
    left_coeff: list[float] | None
    right_coeff: list[float] | None
    center_coeff: list[float] | None
    left_points: list[tuple[float, float]]
    right_points: list[tuple[float, float]]
    paired_points: int
    lane_width_px: float
    lane_center_x_px: float
    ego_center_x_px: float
    offset_px: float
    offset_m: float
    heading_deg: float
    confidence: float
    anchor_y_px: float
    status: str
    left_curve: list[tuple[float, float]] = field(default_factory=list)
    right_curve: list[tuple[float, float]] = field(default_factory=list)
    center_curve: list[tuple[float, float]] = field(default_factory=list)


@dataclass(frozen=True)
class LaneVector:
    vector_id: int
    points: list[tuple[float, float]]
    coeff: list[float]
    y_min: float
    y_max: float
    support: int
    length_px: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interpolate YOLOP lane fragments into ego-lane boundaries and visualize near-field lane offset."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", default="T01-Sample")
    parser.add_argument("--frame", type=int, help="Single frame id.")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument(
        "--mask-root",
        type=Path,
        default=Path("artifacts/roadface/yolop_panoptic"),
        help="Root containing <trip>/lane_masks and <trip>/road_masks from run_yolop_panoptic_labels.py.",
    )
    parser.add_argument("--label-dir-name", default="label2_yolop")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/roadface/yolop_lane_offset"))
    parser.add_argument("--mode", choices=("frame", "contact-sheet", "window", "video", "gif", "tuner"), default="frame")
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--lane-width-m", type=float, default=3.7)
    parser.add_argument(
        "--association-method",
        choices=("birdseye", "vector", "scanline"),
        default="birdseye",
        help="birdseye is the CarND-style IPM/sliding-window implementation.",
    )
    parser.add_argument("--roi-top-ratio", type=float, default=0.43)
    parser.add_argument("--offset-y-ratio", type=float, default=0.92)
    parser.add_argument("--scan-step-px", type=int, default=6)
    parser.add_argument("--band-half-height-px", type=int, default=3)
    parser.add_argument("--cluster-gap-px", type=int, default=18)
    parser.add_argument("--min-cluster-pixels", type=int, default=8)
    parser.add_argument("--min-width-ratio", type=float, default=0.18)
    parser.add_argument("--max-width-ratio", type=float, default=0.72)
    parser.add_argument("--fallback-width-ratio", type=float, default=0.46)
    parser.add_argument("--anchor-y-ratio", type=float, default=0.76)
    parser.add_argument("--anchor-search-ratio", type=float, default=0.24)
    parser.add_argument("--bottom-ignore-ratio", type=float, default=0.08)
    parser.add_argument("--min-vector-pixels", type=int, default=20)
    parser.add_argument("--min-vector-height-px", type=int, default=18)
    parser.add_argument("--merge-gap-y-px", type=int, default=52)
    parser.add_argument("--merge-x-tol-px", type=int, default=42)
    parser.add_argument("--merge-angle-deg", type=float, default=28.0)
    parser.add_argument("--vector-anchor-tolerance-px", type=int, default=52)
    parser.add_argument("--fit-degree", type=int, default=2)
    parser.add_argument("--min-fit-points", type=int, default=5)
    parser.add_argument("--max-residual-px", type=float, default=34.0)
    parser.add_argument("--perspective-top-y-ratio", type=float, default=0.60)
    parser.add_argument("--perspective-bottom-y-ratio", type=float, default=0.995)
    parser.add_argument("--perspective-top-half-width-ratio", type=float, default=0.15)
    parser.add_argument("--perspective-bottom-margin-ratio", type=float, default=0.16)
    parser.add_argument("--bird-destination-margin-ratio", type=float, default=0.22)
    parser.add_argument("--bird-offset-y-ratio", type=float, default=0.94)
    parser.add_argument("--bird-width-tolerance", type=float, default=0.34)
    parser.add_argument("--max-width-std-ratio", type=float, default=0.14)
    parser.add_argument("--max-parallel-slope-delta", type=float, default=0.32)
    parser.add_argument("--histogram-top-ratio", type=float, default=0.18)
    parser.add_argument("--histogram-bottom-ratio", type=float, default=0.98)
    parser.add_argument("--histogram-bands", type=int, default=6)
    parser.add_argument("--histogram-smooth-px", type=int, default=9)
    parser.add_argument("--histogram-peak-distance-ratio", type=float, default=0.08)
    parser.add_argument("--sliding-windows", type=int, default=10)
    parser.add_argument("--window-margin-ratio", type=float, default=0.075)
    parser.add_argument("--window-min-pixels", type=int, default=12)
    parser.add_argument("--previous-fit-margin-ratio", type=float, default=0.065)
    parser.add_argument("--min-lane-pixels", type=int, default=60)
    parser.add_argument("--fit-residual-px", type=float, default=18.0)
    parser.add_argument("--temporal-alpha", type=float, default=0.62)
    parser.add_argument("--window-name", default="FleetIQ lane offset")
    return parser.parse_args()


def frame_ids(trip_dir: Path, args: argparse.Namespace) -> list[int]:
    if args.frame is not None:
        return [args.frame]
    ids = sorted(
        int(path.stem)
        for path in (trip_dir / "kitti" / "image_2").iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stem.isdigit()
    )
    selected = [
        frame_id
        for frame_id in ids
        if frame_id >= args.start
        and (args.end is None or frame_id <= args.end)
        and (frame_id - args.start) % max(1, args.stride) == 0
    ]
    return selected


def filter_frame_ids_with_lane_masks(
    trip_dir: Path,
    ids: list[int],
    args: argparse.Namespace,
) -> list[int]:
    mask_dir = args.mask_root / trip_dir.name / "lane_masks"
    available = {
        int(path.stem)
        for path in mask_dir.glob("*.png")
        if path.stem.isdigit()
    } if mask_dir.exists() else set()
    filtered = [frame_id for frame_id in ids if frame_id in available]
    missing_count = len(ids) - len(filtered)
    if missing_count:
        print(
            f"Skipping {missing_count} frame(s) without YOLOP lane masks; "
            f"using {len(filtered)} frame(s) from {mask_dir}"
        )
    if filtered:
        return filtered
    selected_text = f"frame {args.frame:06d}" if args.frame is not None else "the selected range"
    raise SystemExit(
        f"No YOLOP lane masks are available for {selected_text} in {mask_dir}.\n"
        "Generate them first with scripts\\roadface\\run_yolop_panoptic_labels.py."
    )


def load_mask(path: Path, shape_hw: tuple[int, int]) -> np.ndarray | None:
    if not path.exists():
        return None
    mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return None
    h, w = shape_hw
    if mask.shape[:2] != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    return np.where(mask > 0, 255, 0).astype(np.uint8)


def clean_lane_mask(lane_mask: np.ndarray, road_mask: np.ndarray | None, args: argparse.Namespace) -> np.ndarray:
    h, w = lane_mask.shape[:2]
    cleaned = np.where(lane_mask > 0, 255, 0).astype(np.uint8)
    roi = np.zeros_like(cleaned)
    roi[int(args.roi_top_ratio * h) :, :] = 255
    cleaned = cv2.bitwise_and(cleaned, roi)
    if road_mask is not None and np.count_nonzero(road_mask) > 100:
        road = cv2.dilate(road_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)), iterations=1)
        cleaned = cv2.bitwise_and(cleaned, road)
    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (7, 5)),
        iterations=1,
    )
    cleaned = cv2.dilate(
        cleaned,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        iterations=1,
    )
    return cleaned


def grouped_runs(xs: np.ndarray, max_gap: int) -> list[np.ndarray]:
    if xs.size == 0:
        return []
    xs = np.unique(xs.astype(np.int32))
    gaps = np.where(np.diff(xs) > max_gap)[0] + 1
    return [group for group in np.split(xs, gaps) if group.size > 0]


def scanline_clusters(mask: np.ndarray, y: int, args: argparse.Namespace) -> list[tuple[float, int]]:
    h = mask.shape[0]
    y1 = max(0, y - args.band_half_height_px)
    y2 = min(h, y + args.band_half_height_px + 1)
    band = mask[y1:y2]
    columns = np.where(np.count_nonzero(band, axis=0) > 0)[0]
    clusters: list[tuple[float, int]] = []
    for group in grouped_runs(columns, args.cluster_gap_px):
        support = int(np.count_nonzero(band[:, group]))
        if support < args.min_cluster_pixels:
            continue
        clusters.append((float(np.median(group)), support))
    return clusters


def road_center_at_y(road_mask: np.ndarray | None, y: int, fallback_x: float) -> float:
    if road_mask is None:
        return fallback_x
    h = road_mask.shape[0]
    y1 = max(0, y - 2)
    y2 = min(h, y + 3)
    xs = np.where(np.count_nonzero(road_mask[y1:y2], axis=0) > 0)[0]
    if xs.size < 20:
        return fallback_x
    return float((xs.min() + xs.max()) / 2.0)


def select_ego_pair(
    clusters: list[tuple[float, int]],
    expected_center: float,
    expected_width: float | None,
    width_bounds: tuple[float, float],
) -> tuple[float, float] | None:
    if len(clusters) < 2:
        return None
    xs = sorted(float(x) for x, _ in clusters)
    min_width, max_width = width_bounds
    candidates: list[tuple[float, float, float]] = []
    for left_index in range(len(xs) - 1):
        for right_index in range(left_index + 1, len(xs)):
            left = xs[left_index]
            right = xs[right_index]
            width = right - left
            if width < min_width or width > max_width:
                continue
            if not (left <= expected_center <= right):
                continue
            center = (left + right) / 2.0
            cost = abs(center - expected_center) / max(width, 1.0)
            if expected_width is not None:
                cost += 0.45 * abs(width - expected_width) / max(expected_width, 1.0)
            cost += 0.08 * (right_index - left_index - 1)
            candidates.append((cost, left, right))
    if not candidates:
        return None
    _, left, right = min(candidates, key=lambda item: item[0])
    return left, right


def find_anchor_pair(
    lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    args: argparse.Namespace,
    width_bounds: tuple[float, float],
    fallback_width: float,
    ego_x: float,
) -> tuple[int, float, float] | None:
    h, w = lane_mask.shape[:2]
    roi_top = int(args.roi_top_ratio * h)
    bottom_limit = int((1.0 - args.bottom_ignore_ratio) * h)
    anchor_y = int(np.clip(args.anchor_y_ratio * h, roi_top + 1, bottom_limit - 1))
    search_radius = int(max(args.scan_step_px * 2, args.anchor_search_ratio * h / 2.0))
    y_min = max(roi_top + 1, anchor_y - search_radius)
    y_max = min(bottom_limit - 1, anchor_y + search_radius)
    y_values = sorted(
        range(y_min, y_max + 1, max(2, args.scan_step_px)),
        key=lambda y: abs(y - anchor_y),
    )
    candidates: list[tuple[float, int, float, float]] = []
    for y in y_values:
        clusters = scanline_clusters(lane_mask, y, args)
        if len(clusters) < 2:
            continue
        road_center = road_center_at_y(road_mask, y, ego_x)
        pair = select_ego_pair(clusters, road_center, fallback_width, width_bounds)
        if pair is None:
            pair = select_ego_pair(clusters, ego_x, fallback_width, width_bounds)
        if pair is None:
            continue
        left, right = pair
        width = right - left
        center = (left + right) / 2.0
        cost = abs(y - anchor_y) / max(h, 1)
        cost += 0.90 * abs(center - road_center) / max(width, 1.0)
        cost += 0.35 * abs(width - fallback_width) / max(fallback_width, 1.0)
        candidates.append((cost, y, left, right))
    if not candidates:
        return None
    _, y, left, right = min(candidates, key=lambda item: item[0])
    return y, left, right


def trace_lane_from_anchor(
    lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    args: argparse.Namespace,
    anchor: tuple[int, float, float],
    width_bounds: tuple[float, float],
) -> tuple[list[tuple[float, float]], list[tuple[float, float]], int, float, float]:
    h = lane_mask.shape[0]
    roi_top = int(args.roi_top_ratio * h)
    bottom_limit = int((1.0 - args.bottom_ignore_ratio) * h)
    anchor_y, anchor_left, anchor_right = anchor
    expected_width = anchor_right - anchor_left
    expected_center = (anchor_left + anchor_right) / 2.0
    left_points: list[tuple[float, float]] = [(anchor_left, float(anchor_y))]
    right_points: list[tuple[float, float]] = [(anchor_right, float(anchor_y))]
    paired_points = 1

    def step(y_values: list[int], allow_one_side: bool) -> None:
        nonlocal expected_width, expected_center, paired_points
        for y in y_values:
            road_center = road_center_at_y(road_mask, y, expected_center)
            expected_center = 0.86 * expected_center + 0.14 * road_center
            clusters = scanline_clusters(lane_mask, y, args)
            pair = select_ego_pair(clusters, expected_center, expected_width, width_bounds)
            if pair is not None:
                left, right = pair
                width = right - left
                center = (left + right) / 2.0
                if abs(center - expected_center) > 0.42 * max(expected_width, 1.0):
                    continue
                left_points.append((left, float(y)))
                right_points.append((right, float(y)))
                expected_width = 0.88 * expected_width + 0.12 * width
                expected_center = 0.82 * expected_center + 0.18 * center
                paired_points += 1
                continue
            if allow_one_side and clusters:
                xs = [float(x) for x, _ in clusters]
                left_candidates = [x for x in xs if x < expected_center]
                right_candidates = [x for x in xs if x > expected_center]
                if left_candidates and not right_candidates:
                    left = max(left_candidates)
                    right = left + expected_width
                    if abs(((left + right) / 2.0) - expected_center) < 0.50 * expected_width:
                        left_points.append((left, float(y)))
                        right_points.append((right, float(y)))
                elif right_candidates and not left_candidates:
                    right = min(right_candidates)
                    left = right - expected_width
                    if abs(((left + right) / 2.0) - expected_center) < 0.50 * expected_width:
                        left_points.append((left, float(y)))
                        right_points.append((right, float(y)))

    upward = list(range(anchor_y - max(2, args.scan_step_px), roi_top, -max(2, args.scan_step_px)))
    downward = list(range(anchor_y + max(2, args.scan_step_px), bottom_limit, max(2, args.scan_step_px)))
    step(upward, allow_one_side=True)
    step(downward, allow_one_side=False)
    return left_points, right_points, paired_points, expected_width, expected_center


def robust_polyfit_y_to_x(points: list[tuple[float, float]], degree: int, max_residual_px: float) -> np.ndarray | None:
    if len(points) < max(2, degree + 1):
        return None
    arr = np.asarray(points, dtype=np.float64)
    y = arr[:, 1]
    x = arr[:, 0]
    deg = min(degree, len(points) - 1)
    coeff = np.polyfit(y, x, deg=deg)
    for _ in range(2):
        residual = np.abs(np.polyval(coeff, y) - x)
        keep = residual <= max_residual_px
        if int(keep.sum()) < max(2, deg + 1):
            break
        coeff = np.polyfit(y[keep], x[keep], deg=deg)
    return coeff.astype(np.float32)


def eval_poly(coeff: np.ndarray | None, y: np.ndarray | float) -> np.ndarray | float:
    if coeff is None:
        if isinstance(y, np.ndarray):
            return np.full_like(y, np.nan, dtype=np.float32)
        return math.nan
    return np.polyval(coeff, y)


def poly_slope(coeff: np.ndarray, y: float) -> float:
    if coeff.size <= 1:
        return 0.0
    return float(np.polyval(np.polyder(coeff), y))


def vector_x_at(vector: LaneVector, y: float, tolerance_px: float = 0.0) -> float | None:
    if y < vector.y_min - tolerance_px or y > vector.y_max + tolerance_px:
        return None
    value = float(np.polyval(np.asarray(vector.coeff, dtype=np.float32), y))
    return value if math.isfinite(value) else None


def component_centerline_points(
    mask: np.ndarray,
    label_image: np.ndarray,
    label_id: int,
    args: argparse.Namespace,
) -> list[tuple[float, float]]:
    ys, xs = np.where(label_image == label_id)
    if ys.size == 0:
        return []
    points: list[tuple[float, float]] = []
    step = max(2, args.scan_step_px)
    y_min = int(ys.min())
    y_max = int(ys.max())
    for y in range(y_min, y_max + 1, step):
        y1 = max(0, y - args.band_half_height_px)
        y2 = min(mask.shape[0], y + args.band_half_height_px + 1)
        in_band = (ys >= y1) & (ys < y2)
        if int(in_band.sum()) < max(2, args.min_cluster_pixels // 2):
            continue
        points.append((float(np.median(xs[in_band])), float(np.median(ys[in_band]))))
    return points


def lane_vector_length(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    arr = np.asarray(sorted(points, key=lambda point: point[1]), dtype=np.float32)
    diffs = np.diff(arr, axis=0)
    return float(np.linalg.norm(diffs, axis=1).sum())


def make_lane_vector(vector_id: int, points: list[tuple[float, float]], support: int, args: argparse.Namespace) -> LaneVector | None:
    if len(points) < max(2, args.fit_degree + 1):
        return None
    coeff = robust_polyfit_y_to_x(points, args.fit_degree, args.max_residual_px)
    if coeff is None:
        return None
    ys = [point[1] for point in points]
    y_min = float(min(ys))
    y_max = float(max(ys))
    if y_max - y_min < args.min_vector_height_px:
        return None
    return LaneVector(
        vector_id=vector_id,
        points=sorted(points, key=lambda point: point[1]),
        coeff=coeff.astype(float).tolist(),
        y_min=y_min,
        y_max=y_max,
        support=int(support),
        length_px=lane_vector_length(points),
    )


def extract_lane_vectors(lane_mask: np.ndarray, args: argparse.Namespace) -> list[LaneVector]:
    labels_count, label_image, stats, _centroids = cv2.connectedComponentsWithStats(lane_mask, connectivity=8)
    vectors: list[LaneVector] = []
    next_id = 1
    for label_id in range(1, labels_count):
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        height = int(stats[label_id, cv2.CC_STAT_HEIGHT])
        if area < args.min_vector_pixels or height < args.min_vector_height_px:
            continue
        points = component_centerline_points(lane_mask, label_image, label_id, args)
        vector = make_lane_vector(next_id, points, area, args)
        if vector is not None:
            vectors.append(vector)
            next_id += 1
    return vectors


def vector_merge_cost(a: LaneVector, b: LaneVector, args: argparse.Namespace) -> float | None:
    a_coeff = np.asarray(a.coeff, dtype=np.float32)
    b_coeff = np.asarray(b.coeff, dtype=np.float32)
    overlap_min = max(a.y_min, b.y_min)
    overlap_max = min(a.y_max, b.y_max)
    if overlap_min <= overlap_max:
        y_eval = float((overlap_min + overlap_max) / 2.0)
        gap_y = 0.0
    else:
        if a.y_max < b.y_min:
            y_eval = float((a.y_max + b.y_min) / 2.0)
            gap_y = b.y_min - a.y_max
        else:
            y_eval = float((b.y_max + a.y_min) / 2.0)
            gap_y = a.y_min - b.y_max
        if gap_y > args.merge_gap_y_px:
            return None
    ax = float(np.polyval(a_coeff, y_eval))
    bx = float(np.polyval(b_coeff, y_eval))
    if not math.isfinite(ax) or not math.isfinite(bx):
        return None
    dx = abs(ax - bx)
    allowed_dx = args.merge_x_tol_px + 0.25 * gap_y
    if dx > allowed_dx:
        return None
    a_angle = math.degrees(math.atan(poly_slope(a_coeff, y_eval)))
    b_angle = math.degrees(math.atan(poly_slope(b_coeff, y_eval)))
    angle_delta = abs(a_angle - b_angle)
    if angle_delta > args.merge_angle_deg:
        return None
    overlap_bonus = -0.25 if overlap_min <= overlap_max else 0.0
    return dx / max(args.merge_x_tol_px, 1.0) + gap_y / max(args.merge_gap_y_px, 1.0) + angle_delta / max(args.merge_angle_deg, 1.0) + overlap_bonus


def merge_lane_vectors(vectors: list[LaneVector], args: argparse.Namespace) -> list[LaneVector]:
    merged = list(vectors)
    next_id = 1000
    changed = True
    while changed and len(merged) > 1:
        changed = False
        best: tuple[float, int, int] | None = None
        for i in range(len(merged) - 1):
            for j in range(i + 1, len(merged)):
                cost = vector_merge_cost(merged[i], merged[j], args)
                if cost is None:
                    continue
                if best is None or cost < best[0]:
                    best = (cost, i, j)
        if best is None:
            break
        _cost, i, j = best
        points = [*merged[i].points, *merged[j].points]
        support = merged[i].support + merged[j].support
        replacement = make_lane_vector(next_id, points, support, args)
        next_id += 1
        if replacement is None:
            break
        merged = [vector for index, vector in enumerate(merged) if index not in {i, j}]
        merged.append(replacement)
        changed = True
    return sorted(merged, key=lambda vector: (vector.y_min, vector.y_max, vector.vector_id))


def choose_ego_vector_pair(
    vectors: list[LaneVector],
    road_mask: np.ndarray | None,
    args: argparse.Namespace,
    image_shape: tuple[int, int],
    width_bounds: tuple[float, float],
    fallback_width: float,
) -> tuple[LaneVector, LaneVector, float] | None:
    h, w = image_shape
    ego_x = w / 2.0
    anchor_y = float(np.clip(args.anchor_y_ratio * h, args.roi_top_ratio * h, (1.0 - args.bottom_ignore_ratio) * h))
    center_ref = road_center_at_y(road_mask, int(anchor_y), ego_x)
    min_width, max_width = width_bounds
    candidates: list[tuple[float, LaneVector, LaneVector, float]] = []
    tolerance = float(args.vector_anchor_tolerance_px)
    for left_index in range(len(vectors) - 1):
        for right_index in range(left_index + 1, len(vectors)):
            a = vectors[left_index]
            b = vectors[right_index]
            ax = vector_x_at(a, anchor_y, tolerance)
            bx = vector_x_at(b, anchor_y, tolerance)
            if ax is None or bx is None:
                continue
            left_vector, right_vector = (a, b) if ax <= bx else (b, a)
            left_x, right_x = sorted((ax, bx))
            width = right_x - left_x
            if width < min_width or width > max_width:
                continue
            if not (left_x <= center_ref <= right_x or left_x <= ego_x <= right_x):
                continue
            center = (left_x + right_x) / 2.0
            support = left_vector.length_px + right_vector.length_px + 0.015 * (left_vector.support + right_vector.support)
            cost = abs(center - center_ref) / max(width, 1.0)
            cost += 0.35 * abs(width - fallback_width) / max(fallback_width, 1.0)
            cost -= 0.0025 * support
            candidates.append((cost, left_vector, right_vector, anchor_y))
    if not candidates:
        return None
    _cost, left, right, y = min(candidates, key=lambda item: item[0])
    return left, right, y


def estimate_lane_offset_from_vectors(
    lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    args: argparse.Namespace,
) -> LaneOffsetEstimate | None:
    h, w = lane_mask.shape[:2]
    ego_x = w / 2.0
    min_width = args.min_width_ratio * w
    max_width = args.max_width_ratio * w
    fallback_width = args.fallback_width_ratio * w
    vectors = merge_lane_vectors(extract_lane_vectors(lane_mask, args), args)
    pair = choose_ego_vector_pair(vectors, road_mask, args, (h, w), (min_width, max_width), fallback_width)
    if pair is None:
        return None
    left_vector, right_vector, anchor_y = pair
    left_arr = np.asarray(left_vector.coeff, dtype=np.float32)
    right_arr = np.asarray(right_vector.coeff, dtype=np.float32)
    if left_arr.size != right_arr.size:
        size = max(left_arr.size, right_arr.size)
        left_arr = np.pad(left_arr, (size - left_arr.size, 0), constant_values=0)
        right_arr = np.pad(right_arr, (size - right_arr.size, 0), constant_values=0)
    center_coeff = ((left_arr + right_arr) / 2.0).astype(np.float32)
    y_ref = float(np.clip(args.offset_y_ratio * h, 0, h - 1))
    left_x = float(np.polyval(left_arr, y_ref))
    right_x = float(np.polyval(right_arr, y_ref))
    lane_center_x = float(np.polyval(center_coeff, y_ref))
    lane_width_px = max(abs(right_x - left_x), 1.0)
    px_per_m = lane_width_px / max(args.lane_width_m, 1e-6)
    offset_px = ego_x - lane_center_x
    offset_m = offset_px / px_per_m
    derivative = float(np.polyval(np.polyder(center_coeff), y_ref)) if center_coeff.size > 1 else 0.0
    heading_deg = float(math.degrees(math.atan2(1.0, max(abs(derivative), 1e-6))) - 90.0)
    support_score = min(1.0, (left_vector.length_px + right_vector.length_px) / max(0.55 * h, 1.0))
    width_score = 1.0 if min_width <= lane_width_px <= max_width else 0.45
    confidence = float(np.clip(0.18 + 0.60 * support_score + 0.22 * width_score, 0.05, 0.98))
    return LaneOffsetEstimate(
        left_coeff=left_arr.astype(float).tolist(),
        right_coeff=right_arr.astype(float).tolist(),
        center_coeff=center_coeff.astype(float).tolist(),
        left_points=left_vector.points,
        right_points=right_vector.points,
        paired_points=len(left_vector.points) + len(right_vector.points),
        lane_width_px=float(lane_width_px),
        lane_center_x_px=float(lane_center_x),
        ego_center_x_px=float(ego_x),
        offset_px=float(offset_px),
        offset_m=float(offset_m),
        heading_deg=float(heading_deg),
        confidence=confidence,
        anchor_y_px=float(anchor_y),
        status=f"vector_assoc lanes={len(vectors)}",
    )


def estimate_lane_offset_scanline(
    lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    args: argparse.Namespace,
) -> LaneOffsetEstimate:
    h, w = lane_mask.shape[:2]
    ego_x = w / 2.0
    min_width = args.min_width_ratio * w
    max_width = args.max_width_ratio * w
    fallback_width = args.fallback_width_ratio * w
    anchor = find_anchor_pair(lane_mask, road_mask, args, (min_width, max_width), fallback_width, ego_x)
    if anchor is None:
        expected_width = fallback_width
        left_points: list[tuple[float, float]] = []
        right_points: list[tuple[float, float]] = []
        paired_points = 0
        anchor_y = float(np.clip(args.anchor_y_ratio * h, 0, h - 1))
    else:
        left_points, right_points, paired_points, expected_width, _expected_center = trace_lane_from_anchor(
            lane_mask,
            road_mask,
            args,
            anchor,
            (min_width, max_width),
        )
        anchor_y = float(anchor[0])

    left_coeff = robust_polyfit_y_to_x(left_points, args.fit_degree, args.max_residual_px)
    right_coeff = robust_polyfit_y_to_x(right_points, args.fit_degree, args.max_residual_px)
    status = "ok"
    if left_coeff is None and right_coeff is None:
        center_x = road_center_at_y(road_mask, int(args.offset_y_ratio * h), ego_x)
        center_coeff = np.asarray([center_x], dtype=np.float32)
        left_coeff = np.asarray([center_x - expected_width / 2.0], dtype=np.float32)
        right_coeff = np.asarray([center_x + expected_width / 2.0], dtype=np.float32)
        status = "fallback_no_anchor" if anchor is None else "fallback_anchor_fit_failed"
    elif left_coeff is None:
        right_coeff_arr = np.asarray(right_coeff, dtype=np.float32)
        left_coeff = right_coeff_arr.copy()
        left_coeff[-1] -= expected_width
        status = "inferred_left_from_right"
    elif right_coeff is None:
        left_coeff_arr = np.asarray(left_coeff, dtype=np.float32)
        right_coeff = left_coeff_arr.copy()
        right_coeff[-1] += expected_width
        status = "inferred_right_from_left"

    left_arr = np.asarray(left_coeff, dtype=np.float32)
    right_arr = np.asarray(right_coeff, dtype=np.float32)
    if left_arr.size != right_arr.size:
        size = max(left_arr.size, right_arr.size)
        left_arr = np.pad(left_arr, (size - left_arr.size, 0), constant_values=0)
        right_arr = np.pad(right_arr, (size - right_arr.size, 0), constant_values=0)
    center_coeff = ((left_arr + right_arr) / 2.0).astype(np.float32)
    y_ref = float(np.clip(args.offset_y_ratio * h, 0, h - 1))
    lane_center_x = float(eval_poly(center_coeff, y_ref))
    left_x = float(eval_poly(left_arr, y_ref))
    right_x = float(eval_poly(right_arr, y_ref))
    lane_width_px = max(abs(right_x - left_x), 1.0)
    px_per_m = lane_width_px / max(args.lane_width_m, 1e-6)
    offset_px = ego_x - lane_center_x
    offset_m = offset_px / px_per_m
    derivative = float(np.polyval(np.polyder(center_coeff), y_ref)) if center_coeff.size > 1 else 0.0
    heading_deg = float(math.degrees(math.atan2(1.0, max(abs(derivative), 1e-6))) - 90.0)
    support_score = min(1.0, paired_points / max(args.min_fit_points, 1))
    width_score = 1.0 if min_width <= lane_width_px <= max_width else 0.45
    confidence = float(np.clip(0.15 + 0.65 * support_score + 0.20 * width_score, 0.05, 0.98))
    if status != "ok":
        confidence = min(confidence, 0.72)
    return LaneOffsetEstimate(
        left_coeff=left_arr.astype(float).tolist(),
        right_coeff=right_arr.astype(float).tolist(),
        center_coeff=center_coeff.astype(float).tolist(),
        left_points=left_points,
        right_points=right_points,
        paired_points=paired_points,
        lane_width_px=float(lane_width_px),
        lane_center_x_px=float(lane_center_x),
        ego_center_x_px=float(ego_x),
        offset_px=float(offset_px),
        offset_m=float(offset_m),
        heading_deg=float(heading_deg),
        confidence=confidence,
        anchor_y_px=anchor_y,
        status=status,
    )


def estimate_lane_offset_birdseye(
    lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    args: argparse.Namespace,
    tracker: BirdEyeLaneTracker | None,
) -> LaneOffsetEstimate | None:
    result = detect_birdseye_lane(lane_mask, road_mask, args, tracker)
    if result is None:
        return None
    h, w = lane_mask.shape[:2]
    y_ref = float(np.clip(args.offset_y_ratio * h, 0, h - 1))
    left_x = float(np.polyval(result.left_coeff_image, y_ref))
    right_x = float(np.polyval(result.right_coeff_image, y_ref))
    center_x = float(np.polyval(result.center_coeff_image, y_ref))
    return LaneOffsetEstimate(
        left_coeff=result.left_coeff_image.astype(float).tolist(),
        right_coeff=result.right_coeff_image.astype(float).tolist(),
        center_coeff=result.center_coeff_image.astype(float).tolist(),
        left_points=result.left_curve_image,
        right_points=result.right_curve_image,
        paired_points=int(result.left_pixels[0].size + result.right_pixels[0].size),
        lane_width_px=max(abs(right_x - left_x), 1.0),
        lane_center_x_px=center_x,
        ego_center_x_px=w / 2.0,
        offset_px=w / 2.0 - center_x,
        offset_m=result.offset_m,
        heading_deg=result.heading_deg,
        confidence=result.confidence,
        anchor_y_px=result.anchor_y_image,
        status=result.status,
        left_curve=result.left_curve_image,
        right_curve=result.right_curve_image,
        center_curve=result.center_curve_image,
    )


def estimate_lane_offset(
    lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    args: argparse.Namespace,
    tracker: BirdEyeLaneTracker | None = None,
) -> LaneOffsetEstimate:
    method = getattr(args, "association_method", "birdseye")
    if method == "birdseye":
        birdseye_estimate = estimate_lane_offset_birdseye(lane_mask, road_mask, args, tracker)
        if birdseye_estimate is not None:
            return birdseye_estimate
        fallback = estimate_lane_offset_scanline(lane_mask, road_mask, args)
        return LaneOffsetEstimate(
            left_coeff=fallback.left_coeff,
            right_coeff=fallback.right_coeff,
            center_coeff=fallback.center_coeff,
            left_points=fallback.left_points,
            right_points=fallback.right_points,
            paired_points=fallback.paired_points,
            lane_width_px=fallback.lane_width_px,
            lane_center_x_px=fallback.lane_center_x_px,
            ego_center_x_px=fallback.ego_center_x_px,
            offset_px=fallback.offset_px,
            offset_m=fallback.offset_m,
            heading_deg=fallback.heading_deg,
            confidence=min(fallback.confidence, 0.35),
            anchor_y_px=fallback.anchor_y_px,
            status=f"birdseye_failed:{fallback.status}",
        )
    if method == "vector":
        vector_estimate = estimate_lane_offset_from_vectors(lane_mask, road_mask, args)
        if vector_estimate is not None:
            return vector_estimate
    fallback = estimate_lane_offset_scanline(lane_mask, road_mask, args)
    if method == "vector":
        return LaneOffsetEstimate(
            left_coeff=fallback.left_coeff,
            right_coeff=fallback.right_coeff,
            center_coeff=fallback.center_coeff,
            left_points=fallback.left_points,
            right_points=fallback.right_points,
            paired_points=fallback.paired_points,
            lane_width_px=fallback.lane_width_px,
            lane_center_x_px=fallback.lane_center_x_px,
            ego_center_x_px=fallback.ego_center_x_px,
            offset_px=fallback.offset_px,
            offset_m=fallback.offset_m,
            heading_deg=fallback.heading_deg,
            confidence=min(fallback.confidence, 0.66),
            anchor_y_px=fallback.anchor_y_px,
            status=f"vector_fallback:{fallback.status}",
        )
    return fallback


def coeff_array(values: list[float] | None) -> np.ndarray | None:
    return None if values is None else np.asarray(values, dtype=np.float32)


def draw_fit_line(image: np.ndarray, coeff: np.ndarray | None, y_top: int, color: tuple[int, int, int], thickness: int) -> None:
    if coeff is None:
        return
    h, w = image.shape[:2]
    ys = np.linspace(h - 1, y_top, num=80, dtype=np.float32)
    xs = np.polyval(coeff, ys)
    points = []
    for x, y in zip(xs, ys):
        if np.isfinite(x) and -0.2 * w <= x <= 1.2 * w:
            points.append((int(np.clip(round(x), 0, w - 1)), int(np.clip(round(y), 0, h - 1))))
    if len(points) >= 2:
        cv2.polylines(image, [np.asarray(points, dtype=np.int32)], False, color, thickness, cv2.LINE_AA)


def draw_curve(
    image: np.ndarray,
    curve: list[tuple[float, float]],
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    h, w = image.shape[:2]
    points = [
        (int(np.clip(round(x), 0, w - 1)), int(np.clip(round(y), 0, h - 1)))
        for x, y in curve
        if math.isfinite(x) and math.isfinite(y)
    ]
    if len(points) >= 2:
        cv2.polylines(image, [np.asarray(points, dtype=np.int32)], False, color, thickness, cv2.LINE_AA)


def corridor_mask_from_estimate(shape_hw: tuple[int, int], estimate: LaneOffsetEstimate, y_top: int) -> np.ndarray:
    h, w = shape_hw
    if estimate.left_curve and estimate.right_curve:
        left_pts = [
            (int(np.clip(round(x), 0, w - 1)), int(np.clip(round(y), 0, h - 1)))
            for x, y in estimate.left_curve
            if y >= y_top
        ]
        right_pts = [
            (int(np.clip(round(x), 0, w - 1)), int(np.clip(round(y), 0, h - 1)))
            for x, y in estimate.right_curve
            if y >= y_top
        ]
        mask = np.zeros((h, w), dtype=np.uint8)
        if len(left_pts) >= 2 and len(right_pts) >= 2:
            polygon = np.asarray([*left_pts, *reversed(right_pts)], dtype=np.int32)
            cv2.fillPoly(mask, [polygon], 255)
        return mask
    left = coeff_array(estimate.left_coeff)
    right = coeff_array(estimate.right_coeff)
    if left is None or right is None:
        return np.zeros((h, w), dtype=np.uint8)
    ys = np.linspace(h - 1, y_top, num=80, dtype=np.float32)
    left_pts = []
    right_pts = []
    for y in ys:
        lx = float(np.polyval(left, y))
        rx = float(np.polyval(right, y))
        if not np.isfinite(lx) or not np.isfinite(rx):
            continue
        left_pts.append((int(np.clip(round(lx), 0, w - 1)), int(np.clip(round(y), 0, h - 1))))
        right_pts.append((int(np.clip(round(rx), 0, w - 1)), int(np.clip(round(y), 0, h - 1))))
    mask = np.zeros((h, w), dtype=np.uint8)
    if len(left_pts) >= 2 and len(right_pts) >= 2:
        polygon = np.asarray([*left_pts, *reversed(right_pts)], dtype=np.int32)
        cv2.fillPoly(mask, [polygon], 255)
    return mask


def render_frame(
    image: np.ndarray,
    raw_lane_mask: np.ndarray,
    road_mask: np.ndarray | None,
    cleaned_lane_mask: np.ndarray,
    estimate: LaneOffsetEstimate,
    detections: list,
    caption: str,
    args: argparse.Namespace,
) -> np.ndarray:
    output = image.copy()
    h, w = output.shape[:2]
    y_top = int(args.roi_top_ratio * h)
    if road_mask is not None:
        road_tint = np.zeros_like(output)
        road_tint[:, :, 1] = 170
        output = np.where(road_mask[:, :, None] > 0, cv2.addWeighted(output, 0.78, road_tint, 0.22, 0), output)
    corridor = corridor_mask_from_estimate((h, w), estimate, y_top)
    corridor_tint = np.zeros_like(output)
    corridor_tint[:, :, 0] = 220
    corridor_tint[:, :, 1] = 190
    output = np.where(corridor[:, :, None] > 0, cv2.addWeighted(output, 0.68, corridor_tint, 0.32, 0), output)
    raw_tint = np.zeros_like(output)
    raw_tint[:, :, 1] = 255
    raw_tint[:, :, 2] = 255
    output = np.where(raw_lane_mask[:, :, None] > 0, raw_tint, output)
    cleaned_tint = np.zeros_like(output)
    cleaned_tint[:, :, 2] = 255
    cleaned_tint[:, :, 1] = 120
    output = np.where(cleaned_lane_mask[:, :, None] > 0, cv2.addWeighted(output, 0.65, cleaned_tint, 0.35, 0), output)

    if estimate.left_curve and estimate.right_curve:
        draw_curve(output, estimate.left_curve, (0, 255, 255), 4)
        draw_curve(output, estimate.right_curve, (0, 255, 255), 4)
        draw_curve(output, estimate.center_curve, (255, 80, 40), 3)
    else:
        draw_fit_line(output, coeff_array(estimate.left_coeff), y_top, (0, 255, 255), 4)
        draw_fit_line(output, coeff_array(estimate.right_coeff), y_top, (0, 255, 255), 4)
        draw_fit_line(output, coeff_array(estimate.center_coeff), y_top, (255, 80, 40), 3)
    anchor_y = int(np.clip(round(estimate.anchor_y_px), 0, h - 1))
    bottom_limit = int(np.clip((1.0 - args.bottom_ignore_ratio) * h, 0, h - 1))
    cv2.line(output, (0, anchor_y), (w - 1, anchor_y), (255, 180, 40), 1, cv2.LINE_AA)
    cv2.line(output, (0, bottom_limit), (w - 1, bottom_limit), (80, 80, 255), 1, cv2.LINE_AA)

    y_ref = int(np.clip(args.offset_y_ratio * h, 0, h - 1))
    ego_x = int(round(estimate.ego_center_x_px))
    lane_x = int(np.clip(round(estimate.lane_center_x_px), 0, w - 1))
    cv2.line(output, (ego_x, y_ref - 36), (ego_x, y_ref + 36), (40, 40, 255), 3, cv2.LINE_AA)
    cv2.line(output, (lane_x, y_ref - 42), (lane_x, y_ref + 42), (40, 220, 40), 3, cv2.LINE_AA)
    cv2.arrowedLine(output, (ego_x, y_ref), (lane_x, y_ref), (255, 255, 255), 2, cv2.LINE_AA, tipLength=0.18)

    for det in detections:
        color = CLASS_COLORS.get(det.object_type, (220, 220, 220))
        x1, y1, x2, y2 = [int(round(value)) for value in det.bbox]
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        draw_tag(output, f"{det.object_type}", (x1, max(18, y1 - 4)), color)

    offset_side = "right" if estimate.offset_m > 0 else "left"
    if abs(estimate.offset_m) < 0.03:
        offset_side = "centered"
    draw_tag(
        output,
        f"offset {estimate.offset_m:+.2f}m ({offset_side}) conf={estimate.confidence:.2f}",
        (12, 28),
        (0, 220, 255),
    )
    cv2.rectangle(output, (0, h - 54), (w, h), (20, 25, 30), -1)
    cv2.putText(output, caption, (10, h - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (245, 245, 245), 1, cv2.LINE_AA)
    cv2.putText(
        output,
        f"status={estimate.status} pairs={estimate.paired_points} width={estimate.lane_width_px:.0f}px heading={estimate.heading_deg:+.1f}deg",
        (10, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.44,
        (225, 230, 235),
        1,
        cv2.LINE_AA,
    )
    return output


class FrameSink:
    def __init__(self, args: argparse.Namespace, output_path: Path) -> None:
        self.args = args
        self.output_path = output_path
        self.writer = None
        self.gif_writer = None
        if args.mode == "window":
            cv2.namedWindow(args.window_name, cv2.WINDOW_NORMAL)
        elif args.mode == "gif":
            try:
                import imageio.v2 as imageio
            except ImportError as exc:
                raise RuntimeError("Install imageio or use --mode video/window/frame.") from exc
            self.gif_writer = imageio.get_writer(str(output_path.with_suffix(".gif")), mode="I", duration=1.0 / max(args.fps, 1.0))

    def write(self, frame: np.ndarray) -> bool:
        if self.args.mode == "window":
            cv2.imshow(self.args.window_name, frame)
            key = cv2.waitKey(max(1, int(1000 / max(self.args.fps, 1.0)))) & 0xFF
            return key not in (27, ord("q"))
        if self.args.mode == "video":
            if self.writer is None:
                h, w = frame.shape[:2]
                self.writer = cv2.VideoWriter(
                    str(self.output_path.with_suffix(".mp4")),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    self.args.fps,
                    (w, h),
                )
            self.writer.write(frame)
        elif self.args.mode == "gif":
            assert self.gif_writer is not None
            self.gif_writer.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return True

    def close(self) -> None:
        if self.writer is not None:
            self.writer.release()
        if self.gif_writer is not None:
            self.gif_writer.close()
        if self.args.mode == "window":
            cv2.destroyWindow(self.args.window_name)


class LaneOffsetTuner:
    def __init__(self, trip_dir: Path, frame_ids_: list[int], args: argparse.Namespace) -> None:
        self.trip_dir = trip_dir
        self.frame_ids = frame_ids_
        self.args = args
        self.window = args.window_name
        self.current_index = 0
        self.paused = True
        self.fps = int(np.clip(round(args.fps), 1, 60))
        self.sliding_windows = int(np.clip(args.sliding_windows, 5, 20))
        self.methods = ("birdseye", "vector", "scanline")
        self.method_index = self.methods.index(args.association_method)
        self.last_signature: tuple[int, ...] | None = None
        self.last_parameter_signature: tuple[int, ...] | None = None
        self.last_processed_frame_id: int | None = None
        self.last_rendered: np.ndarray | None = None
        self.last_frame_render: np.ndarray | None = None
        self.last_tick = cv2.getTickCount()
        self.tracker = BirdEyeLaneTracker()
        self.canvas_size = (1440, 760)
        self.control_width = 286
        self.active_slider: str | None = None
        self.slider_regions: dict[str, tuple[int, int, int]] = {}
        self.button_regions: dict[str, tuple[int, int, int, int]] = {}
        self.timeline_region: tuple[int, int, int, int] | None = None
        self.slider_defs = {
            "roi_top_pct": ("Mask ROI top", 30, 70, int(round(args.roi_top_ratio * 100)), "%"),
            "persp_top_y_pct": (
                "IPM top Y",
                45,
                75,
                int(round(args.perspective_top_y_ratio * 100)),
                "%",
            ),
            "persp_top_half_pct": (
                "IPM top half-width",
                6,
                28,
                int(round(args.perspective_top_half_width_ratio * 100)),
                "%",
            ),
            "persp_bottom_margin_pct": (
                "IPM bottom margin",
                5,
                30,
                int(round(args.perspective_bottom_margin_ratio * 100)),
                "%",
            ),
            "bird_dst_margin_pct": (
                "Bird destination margin",
                10,
                35,
                int(round(args.bird_destination_margin_ratio * 100)),
                "%",
            ),
            "window_margin_pct": (
                "Window search margin",
                3,
                15,
                int(round(args.window_margin_ratio * 100)),
                "%",
            ),
            "min_lane_pixels": ("Minimum lane pixels", 20, 180, int(args.min_lane_pixels), " px"),
            "bird_width_tol_pct": (
                "Lane width tolerance",
                15,
                60,
                int(round(args.bird_width_tolerance * 100)),
                "%",
            ),
            "temporal_alpha_pct": (
                "Temporal new-frame weight",
                0,
                100,
                int(round(args.temporal_alpha * 100)),
                "%",
            ),
        }
        self.slider_values = {
            key: int(np.clip(default, minimum, maximum))
            for key, (_label, minimum, maximum, default, _unit) in self.slider_defs.items()
        }
        self.default_slider_values = dict(self.slider_values)
        cv2.namedWindow(self.window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window, *self.canvas_size)
        cv2.setMouseCallback(self.window, self._on_mouse)

    def _effective_args(self) -> argparse.Namespace:
        tuned = argparse.Namespace(**vars(self.args))
        tuned.fps = float(self.fps)
        tuned.association_method = self.methods[self.method_index]
        tuned.roi_top_ratio = self.slider_values["roi_top_pct"] / 100.0
        tuned.perspective_top_y_ratio = self.slider_values["persp_top_y_pct"] / 100.0
        tuned.perspective_top_half_width_ratio = self.slider_values["persp_top_half_pct"] / 100.0
        tuned.perspective_bottom_margin_ratio = self.slider_values["persp_bottom_margin_pct"] / 100.0
        tuned.bird_destination_margin_ratio = self.slider_values["bird_dst_margin_pct"] / 100.0
        tuned.sliding_windows = self.sliding_windows
        tuned.window_margin_ratio = self.slider_values["window_margin_pct"] / 100.0
        tuned.min_lane_pixels = self.slider_values["min_lane_pixels"]
        tuned.bird_width_tolerance = self.slider_values["bird_width_tol_pct"] / 100.0
        tuned.temporal_alpha = self.slider_values["temporal_alpha_pct"] / 100.0
        return tuned

    def _signature(self) -> tuple[int, ...]:
        return (
            self.current_index,
            int(self.paused),
            self.fps,
            self.method_index,
            self.sliding_windows,
            *(self.slider_values[key] for key in self.slider_defs),
        )

    def _parameters_signature(self) -> tuple[int, ...]:
        return (
            self.method_index,
            self.sliding_windows,
            *(self.slider_values[key] for key in self.slider_defs),
        )

    @staticmethod
    def _contains(rect: tuple[int, int, int, int], x: int, y: int) -> bool:
        x1, y1, x2, y2 = rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def _set_frame(self, index: int) -> None:
        self.current_index = int(np.clip(index, 0, len(self.frame_ids) - 1))
        self.last_signature = None

    def _set_slider_from_x(self, key: str, x: int) -> None:
        x1, _y, x2 = self.slider_regions[key]
        _label, minimum, maximum, _default, _unit = self.slider_defs[key]
        ratio = float(np.clip((x - x1) / max(x2 - x1, 1), 0.0, 1.0))
        self.slider_values[key] = int(round(minimum + ratio * (maximum - minimum)))
        self.last_signature = None

    def _handle_button(self, key: str) -> None:
        if key == "play":
            self.paused = not self.paused
            self.last_tick = cv2.getTickCount()
        elif key == "prev":
            self._set_frame(self.current_index - 1)
        elif key == "next":
            self._set_frame(self.current_index + 1)
        elif key == "method":
            self.method_index = (self.method_index + 1) % len(self.methods)
        elif key == "reset":
            self.slider_values = dict(self.default_slider_values)
            self.fps = int(np.clip(round(self.args.fps), 1, 60))
            self.sliding_windows = int(np.clip(self.args.sliding_windows, 5, 20))
            self.method_index = self.methods.index(self.args.association_method)
            self.tracker.reset()
        elif key == "save":
            self._save_current()
        elif key == "fps-":
            self.fps = max(1, self.fps - 1)
        elif key == "fps+":
            self.fps = min(60, self.fps + 1)
        elif key == "windows-":
            self.sliding_windows = max(5, self.sliding_windows - 1)
        elif key == "windows+":
            self.sliding_windows = min(20, self.sliding_windows + 1)
        self.last_signature = None

    def _set_frame_from_timeline(self, x: int) -> None:
        if self.timeline_region is None:
            return
        x1, _y1, x2, _y2 = self.timeline_region
        ratio = float(np.clip((x - x1) / max(x2 - x1, 1), 0.0, 1.0))
        self._set_frame(round(ratio * (len(self.frame_ids) - 1)))

    def _on_mouse(self, event: int, x: int, y: int, flags: int, _param: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            for key, rect in self.button_regions.items():
                if self._contains(rect, x, y):
                    self._handle_button(key)
                    return
            for key, (x1, slider_y, x2) in self.slider_regions.items():
                if x1 - 6 <= x <= x2 + 6 and slider_y - 10 <= y <= slider_y + 10:
                    self.active_slider = key
                    self._set_slider_from_x(key, x)
                    return
            if self.timeline_region is not None and self._contains(self.timeline_region, x, y):
                self._set_frame_from_timeline(x)
        elif event == cv2.EVENT_MOUSEMOVE and self.active_slider is not None and flags & cv2.EVENT_FLAG_LBUTTON:
            self._set_slider_from_x(self.active_slider, x)
        elif event == cv2.EVENT_LBUTTONUP:
            if self.active_slider is not None:
                self._set_slider_from_x(self.active_slider, x)
            self.active_slider = None

    def _draw_button(
        self,
        canvas: np.ndarray,
        key: str,
        label: str,
        rect: tuple[int, int, int, int],
        active: bool = False,
    ) -> None:
        x1, y1, x2, y2 = rect
        fill = (60, 126, 190) if active else (48, 57, 66)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), fill, -1)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (86, 98, 108), 1)
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.39, 1)[0]
        text_x = x1 + max(4, (x2 - x1 - text_size[0]) // 2)
        text_y = y1 + (y2 - y1 + text_size[1]) // 2
        cv2.putText(canvas, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (240, 243, 245), 1, cv2.LINE_AA)
        self.button_regions[key] = rect

    def _draw_slider(self, canvas: np.ndarray, key: str, y: int) -> None:
        label, minimum, maximum, _default, unit = self.slider_defs[key]
        value = self.slider_values[key]
        x1, x2 = 18, self.control_width - 18
        cv2.putText(canvas, label, (x1, y), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (218, 224, 228), 1, cv2.LINE_AA)
        value_text = f"{value}{unit}"
        text_width = cv2.getTextSize(value_text, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)[0][0]
        cv2.putText(
            canvas,
            value_text,
            (x2 - text_width, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (90, 210, 255),
            1,
            cv2.LINE_AA,
        )
        slider_y = y + 15
        cv2.line(canvas, (x1, slider_y), (x2, slider_y), (74, 84, 92), 3, cv2.LINE_AA)
        ratio = (value - minimum) / max(maximum - minimum, 1)
        knob_x = int(round(x1 + ratio * (x2 - x1)))
        cv2.line(canvas, (x1, slider_y), (knob_x, slider_y), (60, 168, 220), 3, cv2.LINE_AA)
        cv2.circle(canvas, (knob_x, slider_y), 5, (230, 240, 245), -1, cv2.LINE_AA)
        self.slider_regions[key] = (x1, slider_y, x2)

    def _compose_ui(
        self,
        rendered: np.ndarray,
        estimate: LaneOffsetEstimate,
        tuned: argparse.Namespace,
    ) -> np.ndarray:
        canvas_w, canvas_h = self.canvas_size
        canvas = np.full((canvas_h, canvas_w, 3), (17, 20, 23), dtype=np.uint8)
        canvas[:, : self.control_width] = (27, 32, 37)
        self.slider_regions.clear()
        self.button_regions.clear()

        gap = 6
        button_w = (self.control_width - 28 - 2 * gap) // 3
        first_x = 14
        top_buttons = [
            ("play", "Play" if self.paused else "Pause", not self.paused),
            ("prev", "Prev", False),
            ("next", "Next", False),
        ]
        for index, (key, label, active) in enumerate(top_buttons):
            x1 = first_x + index * (button_w + gap)
            self._draw_button(canvas, key, label, (x1, 12, x1 + button_w, 40), active)
        second_buttons = [
            ("method", tuned.association_method, tuned.association_method == "birdseye"),
            ("reset", "Reset", False),
            ("save", "Save", False),
        ]
        for index, (key, label, active) in enumerate(second_buttons):
            x1 = first_x + index * (button_w + gap)
            self._draw_button(canvas, key, label, (x1, 46, x1 + button_w, 74), active)

        cv2.putText(
            canvas,
            f"Frame {self.frame_ids[self.current_index]:06d}  ({self.current_index + 1}/{len(self.frame_ids)})",
            (16, 99),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43,
            (235, 239, 242),
            1,
            cv2.LINE_AA,
        )
        self._draw_button(canvas, "fps-", "-", (16, 108, 42, 133))
        cv2.putText(canvas, f"FPS {self.fps}", (50, 126), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (210, 217, 222), 1, cv2.LINE_AA)
        self._draw_button(canvas, "fps+", "+", (108, 108, 134, 133))
        self._draw_button(canvas, "windows-", "-", (150, 108, 176, 133))
        cv2.putText(
            canvas,
            f"Win {self.sliding_windows}",
            (184, 126),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.39,
            (210, 217, 222),
            1,
            cv2.LINE_AA,
        )
        self._draw_button(canvas, "windows+", "+", (246, 108, 272, 133))

        slider_y = 158
        for key in self.slider_defs:
            self._draw_slider(canvas, key, slider_y)
            slider_y += 49

        status_y = canvas_h - 116
        cv2.line(canvas, (14, status_y - 16), (self.control_width - 14, status_y - 16), (55, 64, 72), 1)
        status_lines = [
            f"offset {estimate.offset_m:+.2f} m   conf {estimate.confidence:.2f}",
            f"heading {estimate.heading_deg:+.1f} deg",
            estimate.status[:38],
            "Keys: Space  A/D  S  R  Q",
        ]
        for index, line in enumerate(status_lines):
            cv2.putText(
                canvas,
                line,
                (16, status_y + index * 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.39,
                (220, 226, 230) if index < 3 else (150, 164, 174),
                1,
                cv2.LINE_AA,
            )

        frame_x = self.control_width + 10
        frame_y = 10
        frame_w = canvas_w - frame_x - 10
        frame_h = canvas_h - 62
        scale = min(frame_w / rendered.shape[1], frame_h / rendered.shape[0])
        resized_w = max(1, int(round(rendered.shape[1] * scale)))
        resized_h = max(1, int(round(rendered.shape[0] * scale)))
        resized = cv2.resize(rendered, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)
        paste_x = frame_x + (frame_w - resized_w) // 2
        paste_y = frame_y + (frame_h - resized_h) // 2
        canvas[paste_y : paste_y + resized_h, paste_x : paste_x + resized_w] = resized

        timeline_x1 = frame_x + 18
        timeline_x2 = canvas_w - 22
        timeline_y = canvas_h - 27
        cv2.line(canvas, (timeline_x1, timeline_y), (timeline_x2, timeline_y), (72, 82, 90), 4, cv2.LINE_AA)
        ratio = self.current_index / max(len(self.frame_ids) - 1, 1)
        marker_x = int(round(timeline_x1 + ratio * (timeline_x2 - timeline_x1)))
        cv2.line(canvas, (timeline_x1, timeline_y), (marker_x, timeline_y), (56, 170, 224), 4, cv2.LINE_AA)
        cv2.circle(canvas, (marker_x, timeline_y), 7, (238, 244, 247), -1, cv2.LINE_AA)
        self.timeline_region = (timeline_x1, timeline_y - 12, timeline_x2, timeline_y + 12)
        return canvas

    def _render_current(self) -> np.ndarray | None:
        frame_id = self.frame_ids[self.current_index]
        tuned = self._effective_args()
        parameter_signature = self._parameters_signature()
        if (
            parameter_signature != self.last_parameter_signature
            or self.last_processed_frame_id is None
            or frame_id != self.last_processed_frame_id + max(1, tuned.stride)
        ):
            self.tracker.reset()
        rendered, estimate = process_frame(self.trip_dir, frame_id, tuned, self.tracker)
        if rendered is None or estimate is None:
            return None
        self.last_parameter_signature = parameter_signature
        self.last_processed_frame_id = frame_id
        self.last_frame_render = rendered
        return self._compose_ui(rendered, estimate, tuned)

    def _advance_if_playing(self) -> None:
        if self.paused:
            return
        now = cv2.getTickCount()
        elapsed = (now - self.last_tick) / cv2.getTickFrequency()
        if elapsed < 1.0 / max(self.fps, 1):
            return
        self._set_frame((self.current_index + 1) % len(self.frame_ids))
        self.last_tick = now

    def _save_current(self) -> None:
        if self.last_frame_render is None:
            return
        frame_id = self.frame_ids[self.current_index]
        output = self.args.output_dir / f"{self.trip_dir.name}_{frame_id:06d}_lane_offset_tuned.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output), self.last_frame_render)
        print(f"Wrote {output}")

    def run(self) -> None:
        try:
            while True:
                self._advance_if_playing()
                signature = self._signature()
                if signature != self.last_signature or self.last_rendered is None:
                    rendered = self._render_current()
                    if rendered is not None:
                        self.last_rendered = rendered
                        self.last_signature = signature
                if self.last_rendered is not None:
                    cv2.imshow(self.window, self.last_rendered)
                key = cv2.waitKey(20) & 0xFF
                if key in (27, ord("q")):
                    break
                if key == ord(" "):
                    self._handle_button("play")
                elif key in (ord("a"), ord("A")):
                    self._handle_button("prev")
                elif key in (ord("d"), ord("D")):
                    self._handle_button("next")
                elif key in (ord("s"), ord("S")):
                    self._handle_button("save")
                elif key in (ord("r"), ord("R")):
                    self._handle_button("reset")
        finally:
            cv2.destroyWindow(self.window)


def process_frame(
    trip_dir: Path,
    frame_id: int,
    args: argparse.Namespace,
    tracker: BirdEyeLaneTracker | None = None,
) -> tuple[np.ndarray | None, LaneOffsetEstimate | None]:
    stem = f"{frame_id:06d}"
    image = read_image(find_image(trip_dir / "kitti" / "image_2", stem))
    if image is None:
        return None, None
    h, w = image.shape[:2]
    mask_dir = args.mask_root / trip_dir.name
    lane_mask = load_mask(mask_dir / "lane_masks" / f"{stem}.png", (h, w))
    if lane_mask is None:
        raise FileNotFoundError(f"Missing YOLOP lane mask: {mask_dir / 'lane_masks' / f'{stem}.png'}")
    road_mask = load_mask(mask_dir / "road_masks" / f"{stem}.png", (h, w))
    cleaned = clean_lane_mask(lane_mask, road_mask, args)
    estimate = estimate_lane_offset(cleaned, road_mask, args, tracker)
    calibration = parse_calibration(trip_dir / "kitti" / "calib" / f"{stem}.txt")
    detections = detections_from_labels(
        trip_dir / "kitti" / args.label_dir_name / f"{stem}.txt",
        calibration,
        image.shape,
        source=args.label_dir_name,
    )
    rendered = render_frame(
        image,
        lane_mask,
        road_mask,
        cleaned,
        estimate,
        detections,
        f"{trip_dir.name} frame {stem} | YOLOP lane interpolation",
        args,
    )
    return rendered, estimate


def contact_sheet(frames: list[np.ndarray], columns: int = 3) -> np.ndarray:
    if not frames:
        raise ValueError("No frames to render.")
    target_w, target_h = 640, 360
    tiles = [cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA) for frame in frames]
    rows = (len(tiles) + columns - 1) // columns
    blank = np.full_like(tiles[0], 22)
    tiles.extend([blank] * (rows * columns - len(tiles)))
    return np.vstack([np.hstack(tiles[row * columns : (row + 1) * columns]) for row in range(rows)])


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    ids = filter_frame_ids_with_lane_masks(trip_dir, frame_ids(trip_dir, args), args)
    if args.max_frames is not None:
        ids = ids[: args.max_frames]
    if not ids:
        raise SystemExit("No selected frames.")
    if args.mode == "tuner":
        LaneOffsetTuner(trip_dir, ids, args).run()
        return
    output_base = args.output_dir / f"{trip_dir.name}_lane_offset_{args.mode}"
    output_base.parent.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / f"{trip_dir.name}_lane_offset.csv"
    rendered_frames: list[np.ndarray] = []
    sink = FrameSink(args, output_base) if args.mode in {"window", "video", "gif"} else None
    fieldnames = [
        "trip",
        "frame",
        "offset_m",
        "offset_px",
        "lane_center_x_px",
        "lane_width_px",
        "heading_deg",
        "confidence",
        "paired_points",
        "status",
    ]
    rows: list[dict[str, object]] = []
    tracker = BirdEyeLaneTracker() if args.association_method == "birdseye" else None
    previous_frame_id: int | None = None
    try:
        for frame_id in ids:
            if (
                tracker is not None
                and previous_frame_id is not None
                and frame_id != previous_frame_id + max(1, args.stride)
            ):
                tracker.reset()
            rendered, estimate = process_frame(trip_dir, frame_id, args, tracker)
            previous_frame_id = frame_id
            if rendered is None or estimate is None:
                continue
            rows.append(
                {
                    "trip": trip_dir.name,
                    "frame": frame_id,
                    "offset_m": round(estimate.offset_m, 4),
                    "offset_px": round(estimate.offset_px, 2),
                    "lane_center_x_px": round(estimate.lane_center_x_px, 2),
                    "lane_width_px": round(estimate.lane_width_px, 2),
                    "heading_deg": round(estimate.heading_deg, 4),
                    "confidence": round(estimate.confidence, 4),
                    "paired_points": estimate.paired_points,
                    "status": estimate.status,
                }
            )
            if args.mode == "frame":
                output = args.output_dir / f"{trip_dir.name}_{frame_id:06d}_lane_offset.png"
                cv2.imwrite(str(output), rendered)
                print(f"Wrote {output}")
                break
            if args.mode == "contact-sheet":
                rendered_frames.append(rendered)
            elif sink is not None and not sink.write(rendered):
                break
    finally:
        if sink is not None:
            sink.close()

    if args.mode == "contact-sheet":
        output = output_base.with_suffix(".png")
        cv2.imwrite(str(output), contact_sheet(rendered_frames))
        print(f"Wrote {output}")
    elif args.mode == "video":
        print(f"Wrote {output_base.with_suffix('.mp4')}")
    elif args.mode == "gif":
        print(f"Wrote {output_base.with_suffix('.gif')}")
    if rows:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with metrics_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
