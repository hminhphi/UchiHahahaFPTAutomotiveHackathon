from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from fleetiq_training_roadface.experimental import (
    find_image,
    load_gt_depth,
    parse_calibration,
    read_image,
    resolve_trip,
)


LANE_WIDTH_M = 3.7
PANEL_W = 520
TEXT = (238, 243, 248)
MUTED = (154, 166, 178)
GREEN = (80, 220, 150)
CYAN = (40, 210, 255)
AMBER = (45, 185, 245)
RED = (80, 90, 255)
BLUE = (235, 160, 50)
BG = (18, 24, 32)
PANEL = (29, 38, 49)


@dataclass
class LaneEstimate:
    name: str
    valid: bool
    left_bottom: float = math.nan
    right_bottom: float = math.nan
    left_top: float = math.nan
    right_top: float = math.nan
    offset_m: float = math.nan
    confidence: float = 0.0
    binary: np.ndarray | None = None
    note: str = ""


@dataclass
class FusedLane:
    estimate: LaneEstimate
    probabilities: tuple[float, float, float]
    selected_model: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Demo lane corridor and lane offset using MMAE-style model gating."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", default="T06-Sample")
    parser.add_argument("--mode", choices=("frame", "video", "window"), default="frame")
    parser.add_argument("--frame", type=int, default=100)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--history-sigma-m", type=float, default=0.35)
    return parser.parse_args()


def roi_polygon(width: int, height: int) -> np.ndarray:
    return np.array(
        [
            [int(0.08 * width), height - 1],
            [int(0.44 * width), int(0.53 * height)],
            [int(0.56 * width), int(0.53 * height)],
            [int(0.92 * width), height - 1],
        ],
        dtype=np.int32,
    )


def apply_roi(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape[:2]
    roi = np.zeros_like(mask)
    cv2.fillPoly(roi, [roi_polygon(w, h)], 255)
    return cv2.bitwise_and(mask, roi)


def line_x_at_y(line: tuple[float, float], y: float) -> float:
    slope, intercept = line
    if abs(slope) < 1e-6:
        return math.nan
    return float((y - intercept) / slope)


def line_from_segment(segment: np.ndarray) -> tuple[float, float] | None:
    x1, y1, x2, y2 = [float(v) for v in segment]
    if abs(x2 - x1) < 1e-6:
        return None
    slope = (y2 - y1) / (x2 - x1)
    if abs(slope) < 0.28:
        return None
    return slope, y1 - slope * x1


def fit_line_from_points(points: np.ndarray) -> tuple[float, float] | None:
    if len(points) < 20:
        return None
    y = points[:, 1].astype(np.float64)
    x = points[:, 0].astype(np.float64)
    try:
        slope, intercept = np.polyfit(x, y, 1)
    except (np.linalg.LinAlgError, ValueError):
        return None
    if abs(slope) < 0.25:
        return None
    return float(slope), float(intercept)


def select_lane_pair_from_hough(
    mask: np.ndarray,
    image_shape: tuple[int, int, int],
    threshold: int,
    min_line_length: int,
    max_line_gap: int,
) -> tuple[tuple[float, float] | None, tuple[float, float] | None, int, str]:
    h, w = image_shape[:2]
    y_bottom = h - 1
    center = w / 2.0
    lines = cv2.HoughLinesP(
        mask,
        rho=1,
        theta=np.pi / 180,
        threshold=threshold,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )
    candidates: list[tuple[float, tuple[float, float], np.ndarray, float]] = []
    for raw in [] if lines is None else np.asarray(lines).reshape(-1, 4):
        line = line_from_segment(raw)
        if line is None:
            continue
        xb = line_x_at_y(line, y_bottom)
        if not math.isfinite(xb) or not (-0.15 * w <= xb <= 1.15 * w):
            continue
        length = float(np.hypot(raw[2] - raw[0], raw[3] - raw[1]))
        candidates.append((xb, line, raw.astype(np.float32), length))

    left = [item for item in candidates if item[0] < center - 10 and item[1][0] < 0]
    right = [item for item in candidates if item[0] > center + 10 and item[1][0] > 0]
    if not left or not right:
        return None, None, len(candidates), "no bracket pair"

    expected_width = 0.46 * w
    best_score = float("inf")
    best_pair: tuple[tuple[float, tuple[float, float], np.ndarray, float], tuple[float, tuple[float, float], np.ndarray, float]] | None = None
    for left_item in left:
        for right_item in right:
            lb, rb = left_item[0], right_item[0]
            width = rb - lb
            if width < 0.20 * w or width > 0.82 * w:
                continue
            lane_center = (lb + rb) / 2.0
            width_score = abs(width - expected_width) / expected_width
            center_score = abs(lane_center - center) / max(expected_width, 1.0)
            length_bonus = min(1.0, (left_item[3] + right_item[3]) / (0.7 * w))
            score = width_score + 0.85 * center_score - 0.25 * length_bonus
            if score < best_score:
                best_score = score
                best_pair = (left_item, right_item)

    if best_pair is None:
        return None, None, len(candidates), "no plausible width"

    return best_pair[0][1], best_pair[1][1], len(candidates), "selected center-bracketing pair"


def estimate_from_lines(
    name: str,
    image_shape: tuple[int, int, int],
    left_line: tuple[float, float] | None,
    right_line: tuple[float, float] | None,
    evidence: int,
    binary: np.ndarray | None,
    note: str,
) -> LaneEstimate:
    h, w = image_shape[:2]
    y_bottom = h - 1
    y_top = int(0.56 * h)
    if left_line is None or right_line is None:
        return LaneEstimate(name=name, valid=False, binary=binary, note=f"no fitted bracket pair ({note})")
    lb = line_x_at_y(left_line, y_bottom)
    rb = line_x_at_y(right_line, y_bottom)
    lt = line_x_at_y(left_line, y_top)
    rt = line_x_at_y(right_line, y_top)
    if not all(math.isfinite(v) for v in (lb, rb, lt, rt)):
        return LaneEstimate(name=name, valid=False, binary=binary, note="bad line geometry")
    if rb <= lb or rb - lb < 0.18 * w or rb - lb > 0.95 * w:
        return LaneEstimate(name=name, valid=False, binary=binary, note="implausible lane width")
    if rt <= lt or abs(rt - lt) > 0.75 * (rb - lb):
        top_center = (lt + rt) / 2.0
        top_width = float(np.clip(0.22 * (rb - lb), 0.07 * w, 0.18 * w))
        lt = top_center - top_width / 2.0
        rt = top_center + top_width / 2.0
    lane_center_px = (lb + rb) / 2.0
    px_per_m = (rb - lb) / LANE_WIDTH_M
    offset_m = float((w / 2.0 - lane_center_px) / max(px_per_m, 1e-6))
    if abs(offset_m) > 1.8:
        return LaneEstimate(name=name, valid=False, binary=binary, note=f"offset outlier {offset_m:+.2f}m")
    width_score = 1.0 - min(1.0, abs((rb - lb) - 0.48 * w) / (0.48 * w))
    evidence_score = min(1.0, evidence / 1200.0)
    confidence = float(np.clip(0.25 + 0.45 * width_score + 0.30 * evidence_score, 0.0, 1.0))
    return LaneEstimate(
        name=name,
        valid=True,
        left_bottom=lb,
        right_bottom=rb,
        left_top=lt,
        right_top=rt,
        offset_m=offset_m,
        confidence=confidence,
        binary=binary,
        note=note,
    )


def hough_lane_model(image: np.ndarray) -> LaneEstimate:
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 55, 155)
    edges = apply_roi(edges)
    left_line, right_line, evidence, note = select_lane_pair_from_hough(
        edges,
        image.shape,
        threshold=28,
        min_line_length=max(28, w // 16),
        max_line_gap=42,
    )
    return estimate_from_lines(
        "Model 1: Hough/edge",
        image.shape,
        left_line,
        right_line,
        evidence * 80,
        edges,
        note,
    )


def threshold_lane_model(image: np.ndarray) -> LaneEstimate:
    hls = cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    h_channel, l_channel, s_channel = cv2.split(hls)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    abs_sobel = np.absolute(sobel_x)
    sobel_scaled = np.uint8(255 * abs_sobel / max(float(abs_sobel.max()), 1.0))

    yellow = ((h_channel >= 12) & (h_channel <= 42) & (s_channel > 70) & (l_channel > 80)).astype(np.uint8) * 255
    sobel = ((sobel_scaled > 35) & (sobel_scaled < 220)).astype(np.uint8) * 255
    binary = cv2.bitwise_or(yellow, sobel)
    binary = apply_roi(binary)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    h, w = binary.shape[:2]
    left_line, right_line, evidence, note = select_lane_pair_from_hough(
        binary,
        image.shape,
        threshold=24,
        min_line_length=max(24, w // 18),
        max_line_gap=55,
    )
    return estimate_from_lines(
        "Model 2: HSV/Sobel",
        image.shape,
        left_line,
        right_line,
        evidence * 80,
        binary,
        note,
    )


def corridor_prior_lane(image: np.ndarray) -> LaneEstimate:
    h, w = image.shape[:2]
    lb, rb = 0.30 * w, 0.70 * w
    lt, rt = 0.46 * w, 0.54 * w
    px_per_m = (rb - lb) / LANE_WIDTH_M
    offset_m = float((w / 2.0 - (lb + rb) / 2.0) / px_per_m)
    return LaneEstimate(
        name="Model 3: corridor prior",
        valid=True,
        left_bottom=lb,
        right_bottom=rb,
        left_top=lt,
        right_top=rt,
        offset_m=offset_m,
        confidence=0.32,
        note="lane-mask prior used when markings are weak",
    )


def project_ground_point(
    x_m: float,
    y_m: float,
    z_m: float,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
) -> tuple[float, float]:
    return fx * x_m / z_m + cx, fy * y_m / z_m + cy


def geometry_lane_model(
    image: np.ndarray,
    trip_dir: Path,
    frame_id: int,
    lane_width_m: float = LANE_WIDTH_M,
    camera_height_m: float = 1.5,
) -> LaneEstimate:
    """Metric ego-lane corridor from KITTI intrinsics and depth sanity.

    The dataset calibration is camera-space KITTI-like: X lateral, Y down,
    Z forward. Object labels place road contact around Y=1.5m, so the
    lane corridor can be rendered by projecting X=+-lane_width/2 on that
    ground plane.
    """
    h, w = image.shape[:2]
    calib = parse_calibration(trip_dir / "kitti" / "calib" / f"{frame_id:06d}.txt")
    p2 = calib.get("P2")
    if p2 is None:
        return corridor_prior_lane(image)
    fx, fy, cx, cy = float(p2[0, 0]), float(p2[1, 1]), float(p2[0, 2]), float(p2[1, 2])
    z_near = max(2.8, fy * camera_height_m / max(h - 8 - cy, 1.0))
    z_far = 65.0
    half_width = lane_width_m / 2.0
    lb, vb = project_ground_point(-half_width, camera_height_m, z_near, fx, fy, cx, cy)
    rb, _ = project_ground_point(half_width, camera_height_m, z_near, fx, fy, cx, cy)
    lt, vt = project_ground_point(-half_width, camera_height_m, z_far, fx, fy, cx, cy)
    rt, _ = project_ground_point(half_width, camera_height_m, z_far, fx, fy, cx, cy)

    depth = load_gt_depth(trip_dir, frame_id, "nearest")
    confidence = 0.62
    note = "metric corridor from calib"
    support_binary: np.ndarray | None = None
    if depth is not None:
        yy, xx = np.indices(depth.shape)
        z = depth.astype(np.float32)
        valid = np.isfinite(z) & (z > 0.5) & (z < 80.0)
        y_cam = (yy - cy) * z / max(fy, 1e-6)
        x_cam = (xx - cx) * z / max(fx, 1e-6)
        in_lane = valid & (np.abs(x_cam) <= half_width + 0.25) & (z >= z_near) & (z <= 45.0)
        ground = in_lane & (np.abs(y_cam - camera_height_m) <= 0.35)
        support_binary = (ground.astype(np.uint8) * 255)
        support = float(ground.sum() / max(1, in_lane.sum()))
        confidence = float(np.clip(0.45 + 0.7 * support, 0.45, 0.92))
        note = f"metric corridor from calib+depth support={support:.2f}"

    return LaneEstimate(
        name="Model 3: metric lane corridor",
        valid=True,
        left_bottom=float(np.clip(lb, 0, w - 1)),
        right_bottom=float(np.clip(rb, 0, w - 1)),
        left_top=float(np.clip(lt, 0, w - 1)),
        right_top=float(np.clip(rt, 0, w - 1)),
        offset_m=0.0,
        confidence=confidence,
        binary=support_binary,
        note=note,
    )


def fuse_estimates(
    model1: LaneEstimate,
    model2: LaneEstimate,
    model3: LaneEstimate,
    previous_offset: float | None,
    sigma_m: float,
    image: np.ndarray,
) -> FusedLane:
    estimates = [model1, model2, model3]
    scores: list[float] = []
    valid_offsets = [est.offset_m for est in estimates if est.valid and math.isfinite(est.offset_m)]
    if previous_offset is not None:
        reference = previous_offset
    elif model3.valid and math.isfinite(model3.offset_m):
        reference = model3.offset_m
    else:
        reference = float(np.median(valid_offsets)) if valid_offsets else 0.0
    for est in estimates:
        if not est.valid or not math.isfinite(est.offset_m):
            scores.append(1e-6)
            continue
        if not est.name.startswith("Model 3") and abs(est.offset_m - model3.offset_m) > 0.75:
            scores.append(1e-6)
            continue
        residual = est.offset_m - reference
        likelihood = math.exp(-0.5 * (residual / max(sigma_m, 1e-3)) ** 2)
        scores.append(max(1e-6, est.confidence * likelihood))
    total = sum(scores)
    if total <= 0:
        probabilities3 = (0.0, 0.0, 1.0)
    else:
        probabilities3 = tuple(score / total for score in scores)
    selected_idx = int(np.argmax(probabilities3))
    selected = estimates[selected_idx]
    if not selected.valid:
        selected = model3
    fused = LaneEstimate(
        name="MMAE-lite fused",
        valid=selected.valid,
        left_bottom=selected.left_bottom,
        right_bottom=selected.right_bottom,
        left_top=selected.left_top,
        right_top=selected.right_top,
        offset_m=selected.offset_m,
        confidence=(
            selected.confidence
            if selected.name.startswith("Model 3")
            else max(selected.confidence, max(probabilities3))
        ),
        note=f"selected {selected.name}",
    )
    return FusedLane(fused, probabilities3, selected.name)


def lane_polygon(est: LaneEstimate) -> np.ndarray | None:
    if not est.valid:
        return None
    return np.array(
        [
            [int(est.left_bottom), 359],
            [int(est.left_top), 202],
            [int(est.right_top), 202],
            [int(est.right_bottom), 359],
        ],
        dtype=np.int32,
    )


def draw_lane_estimate(image: np.ndarray, est: LaneEstimate, color: tuple[int, int, int]) -> np.ndarray:
    out = image.copy()
    h = out.shape[0]
    if est.valid:
        y_bottom = h - 1
        y_top = int(0.56 * h)
        pts = np.array(
            [
                [int(est.left_bottom), y_bottom],
                [int(est.left_top), y_top],
                [int(est.right_top), y_top],
                [int(est.right_bottom), y_bottom],
            ],
            dtype=np.int32,
        )
        overlay = out.copy()
        cv2.fillPoly(overlay, [pts], color)
        out = cv2.addWeighted(out, 0.72, overlay, 0.28, 0)
        cv2.line(out, tuple(pts[0]), tuple(pts[1]), (255, 245, 80), 4, cv2.LINE_AA)
        cv2.line(out, tuple(pts[2]), tuple(pts[3]), (255, 245, 80), 4, cv2.LINE_AA)
        lane_center = int((est.left_bottom + est.right_bottom) / 2.0)
        cv2.line(out, (out.shape[1] // 2, y_bottom), (out.shape[1] // 2, y_bottom - 55), RED, 3, cv2.LINE_AA)
        cv2.line(out, (lane_center, y_bottom), (lane_center, y_bottom - 55), GREEN, 3, cv2.LINE_AA)
    return out


def draw_text(img: np.ndarray, text: str, x: int, y: int, color: tuple[int, int, int] = TEXT, scale: float = 0.55) -> None:
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def binary_to_bgr(binary: np.ndarray | None, shape: tuple[int, int, int]) -> np.ndarray:
    if binary is None:
        return np.full(shape, (22, 28, 36), dtype=np.uint8)
    small = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    small[:, :, 1] = np.maximum(small[:, :, 1], binary)
    return small


def fit_tile(image: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = image.shape[:2]
    scale = min(width / w, height / h)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    canvas = np.full((height, width, 3), BG, dtype=np.uint8)
    y = (height - resized.shape[0]) // 2
    x = (width - resized.shape[1]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def render_demo_frame(
    image: np.ndarray,
    frame_id: int,
    trip_name: str,
    model1: LaneEstimate,
    model2: LaneEstimate,
    model3: LaneEstimate,
    fused: FusedLane,
) -> np.ndarray:
    h, w = image.shape[:2]
    canvas = np.full((720, 1280, 3), BG, dtype=np.uint8)
    fused_view = draw_lane_estimate(image, fused.estimate, BLUE)
    model1_view = draw_lane_estimate(image, model1, CYAN)
    model2_view = draw_lane_estimate(image, model2, AMBER)
    model3_view = draw_lane_estimate(image, model3, BLUE)
    canvas[0:520, 0:740] = fit_tile(fused_view, 740, 520)
    canvas[0:173, 740:1010] = fit_tile(model1_view, 270, 173)
    canvas[173:346, 740:1010] = fit_tile(model2_view, 270, 173)
    canvas[346:520, 740:1010] = fit_tile(model3_view, 270, 174)
    canvas[0:173, 1010:1280] = fit_tile(binary_to_bgr(model1.binary, image.shape), 270, 173)
    canvas[173:346, 1010:1280] = fit_tile(binary_to_bgr(model2.binary, image.shape), 270, 173)
    canvas[346:520, 1010:1280] = fit_tile(binary_to_bgr(model3.binary, image.shape), 270, 174)
    cv2.rectangle(canvas, (0, 520), (1280, 720), PANEL, -1)
    cv2.line(canvas, (0, 520), (1280, 520), (70, 84, 98), 1)
    draw_text(canvas, f"{trip_name} frame {frame_id:06d} | lane offset demo", 24, 552, TEXT, 0.72)
    draw_text(canvas, "Fused view: blue lane mask/prism, red ego center, green lane center", 24, 582, MUTED, 0.52)
    draw_text(canvas, "Model 1", 760, 28, CYAN, 0.55)
    draw_text(canvas, "Model 2", 760, 201, AMBER, 0.55)
    draw_text(canvas, "Model 3", 760, 374, BLUE, 0.55)
    draw_text(canvas, "M1 binary", 1030, 28, CYAN, 0.50)
    draw_text(canvas, "M2 binary", 1030, 201, AMBER, 0.50)
    draw_text(canvas, "M3 depth support", 1030, 374, BLUE, 0.50)
    rows = [
        model_summary(model1),
        model_summary(model2),
        model_summary(model3),
        f"MMAE-lite: offset={format_m(fused.estimate.offset_m)} conf={fused.estimate.confidence:.2f}",
        (
            f"p(M1)={fused.probabilities[0]:.2f}  p(M2)={fused.probabilities[1]:.2f}  "
            f"p(M3)={fused.probabilities[2]:.2f}  selected={fused.selected_model}"
        ),
        "Note: M1/M2 are rejected when lane markings are inconsistent; M3 is ego-lane corridor prior.",
    ]
    for idx, row in enumerate(rows):
        draw_text(canvas, row, 24, 604 + idx * 19, TEXT if idx >= 3 else MUTED, 0.48)
    return canvas


def model_summary(est: LaneEstimate) -> str:
    status = "ok" if est.valid else "fail"
    return f"{est.name}: {status}, offset={format_m(est.offset_m)}, conf={est.confidence:.2f}, {est.note}"


def format_m(value: float) -> str:
    return "--" if not math.isfinite(value) else f"{value:+.2f}m"


def default_output(trip_name: str, mode: str, frame_id: int) -> Path:
    out_dir = Path("artifacts/renders/roadface/lane_demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode == "frame":
        return out_dir / f"{trip_name}_{frame_id:06d}_lane_mmae.png"
    return out_dir / f"{trip_name}_lane_mmae.mp4"


def load_trip_frame(trip_dir: Path, frame_id: int) -> np.ndarray:
    path = find_image(trip_dir / "kitti" / "image_2", f"{frame_id:06d}")
    image = read_image(path)
    if image is None:
        raise FileNotFoundError(f"Missing image_2 frame {frame_id:06d} in {trip_dir}")
    return image


def run_frame(trip_dir: Path, frame_id: int, output: Path, sigma_m: float) -> None:
    image = load_trip_frame(trip_dir, frame_id)
    model1 = hough_lane_model(image)
    model2 = threshold_lane_model(image)
    model3 = geometry_lane_model(image, trip_dir, frame_id)
    fused = fuse_estimates(model1, model2, model3, None, sigma_m, image)
    frame = render_demo_frame(image, frame_id, trip_dir.name, model1, model2, model3, fused)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), frame)
    print(f"Wrote {output.resolve()}")


def run_sequence(
    trip_dir: Path,
    start: int,
    end: int,
    output: Path,
    mode: str,
    fps: float,
    sigma_m: float,
) -> None:
    writer = None
    previous_offset: float | None = None
    try:
        for frame_id in range(start, end + 1):
            image = load_trip_frame(trip_dir, frame_id)
            model1 = hough_lane_model(image)
            model2 = threshold_lane_model(image)
            model3 = geometry_lane_model(image, trip_dir, frame_id)
            fused = fuse_estimates(model1, model2, model3, previous_offset, sigma_m, image)
            if math.isfinite(fused.estimate.offset_m):
                previous_offset = fused.estimate.offset_m
            frame = render_demo_frame(image, frame_id, trip_dir.name, model1, model2, model3, fused)
            if mode == "window":
                cv2.imshow("FleetIQ lane MMAE offset demo", frame)
                if (cv2.waitKey(max(1, int(1000 / fps))) & 0xFF) in (27, ord("q")):
                    break
            else:
                if writer is None:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(
                        str(output),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        fps,
                        (frame.shape[1], frame.shape[0]),
                    )
                writer.write(frame)
            if frame_id == start or (frame_id - start + 1) % 100 == 0:
                print(f"Processed frame {frame_id}")
    finally:
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()
    if mode == "video":
        print(f"Wrote {output.resolve()}")


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    if args.mode == "frame":
        output = (args.output or default_output(trip_dir.name, "frame", args.frame)).resolve()
        run_frame(trip_dir, args.frame, output, args.history_sigma_m)
        return
    end = args.end if args.end is not None else args.start + 200
    output = (args.output or default_output(trip_dir.name, "video", args.start)).resolve()
    run_sequence(trip_dir, args.start, end, output, args.mode, args.fps, args.history_sigma_m)


if __name__ == "__main__":
    main()
