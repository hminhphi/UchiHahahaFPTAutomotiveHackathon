from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from fleetiq_data import load_trip_document
from fleetiq_roadface.geometry import valid_bbox as runtime_valid_bbox
from fleetiq_training_roadface.datasets import (
    discover_trip_dirs,
    resolve_trip_dir,
)


CLASS_NAMES = [
    "Car",
    "Van",
    "Truck",
    "Pedestrian",
    "Cyclist",
    "Motorcycle",
    "Bus",
    "LongVehicle",
]
CLASS_TO_ID = {name: idx for idx, name in enumerate(CLASS_NAMES)}
COCO_TO_KITTI = {
    "car": "Car",
    "truck": "Truck",
    "bus": "Bus",
    "motorcycle": "Motorcycle",
    "bicycle": "Cyclist",
    "person": "Pedestrian",
}
CLASS_COLORS = {
    "Car": (40, 210, 255),
    "Van": (80, 220, 160),
    "Truck": (80, 160, 255),
    "Pedestrian": (80, 90, 255),
    "Cyclist": (255, 160, 80),
    "Motorcycle": (255, 120, 180),
    "Bus": (50, 230, 230),
    "LongVehicle": (180, 120, 255),
}


@dataclass
class KittiObject:
    object_type: str
    truncated: float
    occluded: int
    alpha: float
    bbox: tuple[float, float, float, float]
    dimensions: tuple[float, float, float]
    location: tuple[float, float, float]
    rotation_y: float


@dataclass
class Detection:
    object_type: str
    bbox: tuple[float, float, float, float]
    confidence: float = 1.0
    dimensions: tuple[float, float, float] | None = None
    location: tuple[float, float, float] | None = None
    rotation_y: float | None = None
    source: str = "unknown"
    track_id: int | None = None
    distance_m: float = math.nan
    lateral_m: float = math.nan
    relative_speed_mps: float = math.nan
    ttc_s: float = math.inf
    distance_source: str = "none"


@dataclass
class TrackState:
    track_id: int
    object_type: str
    bbox: tuple[float, float, float, float]
    timestamp: float
    distance_m: float
    missed: int = 0
    history: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class RoadPlane:
    normal: np.ndarray
    d: float
    inlier_ratio: float
    inlier_count: int
    source: str = "depth_ransac"


@dataclass
class PlaneLaneEstimate:
    road_mask: np.ndarray
    lane_mask: np.ndarray
    corridor_mask: np.ndarray
    vertical_corridor_mask: np.ndarray
    lane_offset_m: float
    heading_deg: float
    confidence: float
    plane: RoadPlane
    source: str
    note: str = ""


def discover_trips(dataset: str | Path = "all") -> list[Path]:
    return discover_trip_dirs(dataset)


def resolve_trip(name: str, dataset: str | Path = "all") -> Path:
    return resolve_trip_dir(name, dataset)


def load_trip_doc(trip_dir: Path) -> dict[str, Any]:
    return load_trip_document(trip_dir)


def find_image(directory: Path, stem: str) -> Path | None:
    for suffix in (".jpg", ".png", ".jpeg"):
        path = directory / f"{stem}{suffix}"
        if path.exists():
            return path
    return None


def read_image(path: Path | None) -> np.ndarray | None:
    if path is None:
        return None
    image = cv2.imread(str(path))
    return image


def parse_calibration(path: Path) -> dict[str, np.ndarray]:
    calibration: dict[str, np.ndarray] = {}
    if not path.exists():
        return calibration
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, values = line.partition(":")
        if not values:
            continue
        nums = np.asarray([float(value) for value in values.split()], dtype=np.float64)
        if key.startswith("P") and nums.size == 12:
            calibration[key] = nums.reshape(3, 4)
        elif key == "R0_rect" and nums.size == 9:
            calibration[key] = nums.reshape(3, 3)
        elif nums.size == 12:
            calibration[key] = nums.reshape(3, 4)
        else:
            calibration[key] = nums
    return calibration


def parse_kitti_labels(path: Path) -> list[KittiObject]:
    objects: list[KittiObject] = []
    if not path.exists():
        return objects
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) < 15:
            continue
        values = [float(value) for value in fields[1:]]
        objects.append(
            KittiObject(
                object_type=fields[0],
                truncated=values[0],
                occluded=int(values[1]),
                alpha=values[2],
                bbox=tuple(values[3:7]),
                dimensions=tuple(values[7:10]),
                location=tuple(values[10:13]),
                rotation_y=values[13],
            )
        )
    return objects


def box_3d_corners(obj: KittiObject | Detection) -> np.ndarray | None:
    if obj.dimensions is None or obj.location is None or obj.rotation_y is None:
        return None
    height, width, length = obj.dimensions
    x, y, z = obj.location
    if z <= 0.1:
        return None
    x_corners = np.array([length / 2, length / 2, -length / 2, -length / 2] * 2)
    y_corners = np.array([0, 0, 0, 0, -height, -height, -height, -height])
    z_corners = np.array([width / 2, -width / 2, -width / 2, width / 2] * 2)
    cos_y = math.cos(obj.rotation_y)
    sin_y = math.sin(obj.rotation_y)
    rotation = np.array([[cos_y, 0, sin_y], [0, 1, 0], [-sin_y, 0, cos_y]])
    corners = rotation @ np.vstack([x_corners, y_corners, z_corners])
    corners += np.array([[x], [y], [z]])
    return corners


def project_points(points_3d: np.ndarray, projection: np.ndarray) -> np.ndarray | None:
    if points_3d.shape[0] != 3:
        return None
    homogeneous = np.vstack([points_3d, np.ones((1, points_3d.shape[1]))])
    projected = projection @ homogeneous
    if np.any(projected[2] <= 0.1):
        return None
    return (projected[:2] / projected[2]).T


def bbox_from_projected_object(
    obj: KittiObject, projection: np.ndarray, width: int, height: int
) -> tuple[float, float, float, float] | None:
    corners = box_3d_corners(obj)
    if corners is None:
        return valid_bbox(obj.bbox, width, height)
    points = project_points(corners, projection)
    if points is None:
        return valid_bbox(obj.bbox, width, height)
    x1 = float(np.clip(np.min(points[:, 0]), 0, width - 1))
    y1 = float(np.clip(np.min(points[:, 1]), 0, height - 1))
    x2 = float(np.clip(np.max(points[:, 0]), 0, width - 1))
    y2 = float(np.clip(np.max(points[:, 1]), 0, height - 1))
    return valid_bbox((x1, y1, x2, y2), width, height)


def valid_bbox(
    bbox: Iterable[float], width: int, height: int, min_size: float = 3.0
) -> tuple[float, float, float, float] | None:
    return runtime_valid_bbox(bbox, width, height, min_size)


def detections_from_labels(
    label_path: Path,
    calibration: dict[str, np.ndarray],
    image_shape: tuple[int, int, int],
    source: str = "kitti_label",
) -> list[Detection]:
    h, w = image_shape[:2]
    projection = calibration.get("P2")
    detections: list[Detection] = []
    for obj in parse_kitti_labels(label_path):
        if obj.object_type not in CLASS_TO_ID:
            continue
        bbox = (
            bbox_from_projected_object(obj, projection, w, h)
            if projection is not None
            else valid_bbox(obj.bbox, w, h)
        )
        if bbox is None:
            continue
        loc = obj.location if obj.location[2] > 0.1 else None
        detections.append(
            Detection(
                object_type=obj.object_type,
                bbox=bbox,
                confidence=1.0,
                dimensions=obj.dimensions,
                location=loc,
                rotation_y=obj.rotation_y,
                source=source,
            )
        )
    return detections


def nearest_depth_path(depth_dir: Path, frame_id: int, policy: str = "previous") -> Path | None:
    if not depth_dir.exists():
        return None
    ids = sorted(int(path.stem) for path in depth_dir.glob("*.npy") if path.stem.isdigit())
    if not ids:
        return None
    values = np.asarray(ids, dtype=int)
    if policy == "nearest":
        chosen = int(values[np.argmin(np.abs(values - frame_id))])
    else:
        prev = values[values <= frame_id]
        chosen = int(prev[-1] if prev.size else values[0])
    return depth_dir / f"{chosen:06d}.npy"


def load_gt_depth(trip_dir: Path, frame_id: int, policy: str = "previous") -> np.ndarray | None:
    path = nearest_depth_path(trip_dir / "kitti" / "depth", frame_id, policy)
    if path is None:
        return None
    return np.load(path).astype(np.float32)


def stereo_depth(
    left_bgr: np.ndarray,
    right_bgr: np.ndarray,
    calibration: dict[str, np.ndarray],
    max_depth_m: float = 90.0,
) -> np.ndarray | None:
    p2 = calibration.get("P2")
    p3 = calibration.get("P3")
    if p2 is None or p3 is None:
        return None
    fx = float(p2[0, 0])
    baseline = abs(float(p3[0, 3] / p3[0, 0] - p2[0, 3] / p2[0, 0]))
    if fx <= 0 or baseline <= 0:
        return None
    gray_l = cv2.cvtColor(left_bgr, cv2.COLOR_BGR2GRAY)
    gray_r = cv2.cvtColor(right_bgr, cv2.COLOR_BGR2GRAY)
    matcher = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=128,
        blockSize=7,
        P1=8 * 3 * 7**2,
        P2=32 * 3 * 7**2,
        disp12MaxDiff=1,
        uniquenessRatio=8,
        speckleWindowSize=80,
        speckleRange=24,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
    )
    disparity = matcher.compute(gray_l, gray_r).astype(np.float32) / 16.0
    depth = np.full(disparity.shape, np.nan, dtype=np.float32)
    valid = disparity > 0.5
    depth[valid] = (fx * baseline) / disparity[valid]
    depth[(depth < 0.5) | (depth > max_depth_m)] = np.nan
    return depth


def bbox_depth(depth: np.ndarray | None, bbox: tuple[float, float, float, float]) -> float:
    if depth is None:
        return math.nan
    h, w = depth.shape[:2]
    x1, y1, x2, y2 = [int(round(v)) for v in bbox]
    x1, x2 = sorted((max(0, x1), min(w - 1, x2)))
    y1, y2 = sorted((max(0, y1), min(h - 1, y2)))
    if x2 <= x1 or y2 <= y1:
        return math.nan
    crop = depth[y1:y2, x1:x2]
    valid = crop[np.isfinite(crop) & (crop > 0.5)]
    if valid.size < 20:
        return math.nan
    return float(np.nanmedian(valid))


def estimate_geometry_depth(
    det: Detection, calibration: dict[str, np.ndarray]
) -> float:
    p2 = calibration.get("P2")
    if p2 is None or det.dimensions is None:
        return math.nan
    height_m = max(float(det.dimensions[0]), 0.2)
    bbox_h = max(det.bbox[3] - det.bbox[1], 1.0)
    return float(p2[1, 1] * height_m / bbox_h)


def lateral_from_bbox(
    bbox: tuple[float, float, float, float], distance_m: float, calibration: dict[str, np.ndarray]
) -> float:
    p2 = calibration.get("P2")
    if p2 is None or not math.isfinite(distance_m):
        return math.nan
    cx_img = (bbox[0] + bbox[2]) / 2.0
    fx = float(p2[0, 0])
    cx = float(p2[0, 2])
    if fx <= 0:
        return math.nan
    return float((cx_img - cx) * distance_m / fx)


def attach_distances(
    detections: list[Detection],
    depth: np.ndarray | None,
    calibration: dict[str, np.ndarray],
    prefer_label3d: bool = True,
) -> None:
    for det in detections:
        if prefer_label3d and det.location is not None and det.location[2] > 0.1:
            det.distance_m = float(det.location[2])
            det.lateral_m = float(det.location[0])
            det.distance_source = "label3d"
            continue
        depth_m = bbox_depth(depth, det.bbox)
        if math.isfinite(depth_m):
            det.distance_m = depth_m
            det.lateral_m = lateral_from_bbox(det.bbox, depth_m, calibration)
            det.distance_source = "depth_roi"
            continue
        geom_m = estimate_geometry_depth(det, calibration)
        if math.isfinite(geom_m):
            det.distance_m = geom_m
            det.lateral_m = lateral_from_bbox(det.bbox, geom_m, calibration)
            det.distance_source = "single_view_geometry"


def camera_intrinsics(calibration: dict[str, np.ndarray]) -> tuple[float, float, float, float] | None:
    p2 = calibration.get("P2")
    if p2 is None:
        return None
    fx, fy = float(p2[0, 0]), float(p2[1, 1])
    cx, cy = float(p2[0, 2]), float(p2[1, 2])
    if fx <= 0 or fy <= 0:
        return None
    return fx, fy, cx, cy


def default_road_roi(shape: tuple[int, int] | tuple[int, int, int]) -> np.ndarray:
    h, w = shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    polygon = np.array(
        [
            [int(0.06 * w), h - 1],
            [int(0.42 * w), int(0.50 * h)],
            [int(0.58 * w), int(0.50 * h)],
            [int(0.94 * w), h - 1],
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(mask, [polygon], 255)
    return mask


def backproject_depth_points(
    depth: np.ndarray,
    calibration: dict[str, np.ndarray],
    mask: np.ndarray | None = None,
    max_points: int = 8000,
) -> np.ndarray:
    intr = camera_intrinsics(calibration)
    if intr is None:
        return np.empty((0, 3), dtype=np.float32)
    fx, fy, cx, cy = intr
    h, w = depth.shape[:2]
    yy, xx = np.indices((h, w))
    z = depth.astype(np.float32)
    valid = np.isfinite(z) & (z > 1.0) & (z < 80.0)
    if mask is not None:
        valid &= cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST) > 0
    else:
        valid &= default_road_roi((h, w)) > 0
    x = (xx.astype(np.float32) - cx) * z / fx
    y = (yy.astype(np.float32) - cy) * z / fy
    # Camera-space KITTI convention is X lateral, Y down, Z forward.
    valid &= (y > 0.4) & (y < 3.2)
    points = np.column_stack((x[valid], y[valid], z[valid])).astype(np.float32)
    if points.shape[0] > max_points:
        step = max(1, points.shape[0] // max_points)
        points = points[::step][:max_points]
    return points


def _fit_plane_svd(points: np.ndarray) -> tuple[np.ndarray, float] | None:
    if points.shape[0] < 3:
        return None
    centroid = points.mean(axis=0)
    _, _, vh = np.linalg.svd(points - centroid, full_matrices=False)
    normal = vh[-1].astype(np.float64)
    norm = float(np.linalg.norm(normal))
    if norm < 1e-9:
        return None
    normal /= norm
    if normal[1] < 0:
        normal *= -1.0
    d = -float(normal @ centroid)
    return normal.astype(np.float32), d


def fallback_road_plane(camera_height_m: float = 1.5) -> RoadPlane:
    return RoadPlane(
        normal=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
        d=-float(camera_height_m),
        inlier_ratio=0.0,
        inlier_count=0,
        source="flat_ground_fallback",
    )


def fit_road_plane_ransac(
    depth: np.ndarray | None,
    calibration: dict[str, np.ndarray],
    road_mask: np.ndarray | None = None,
    iterations: int = 96,
    threshold_m: float = 0.10,
    min_points: int = 250,
) -> RoadPlane:
    if depth is None:
        return fallback_road_plane()
    points = backproject_depth_points(depth, calibration, road_mask)
    if points.shape[0] < min_points:
        return fallback_road_plane()
    rng = np.random.default_rng(42)
    best_inliers: np.ndarray | None = None
    best_count = 0
    for _ in range(iterations):
        sample = points[rng.choice(points.shape[0], size=3, replace=False)]
        normal = np.cross(sample[1] - sample[0], sample[2] - sample[0])
        norm = float(np.linalg.norm(normal))
        if norm < 1e-6:
            continue
        normal = normal / norm
        if normal[1] < 0:
            normal *= -1.0
        if normal[1] < 0.45:
            continue
        d = -float(normal @ sample[0])
        distances = np.abs(points @ normal + d)
        inliers = distances < threshold_m
        count = int(inliers.sum())
        if count > best_count:
            best_count = count
            best_inliers = inliers
    if best_inliers is None or best_count < min_points:
        return fallback_road_plane()
    refined = _fit_plane_svd(points[best_inliers])
    if refined is None:
        return fallback_road_plane()
    normal, d = refined
    return RoadPlane(
        normal=normal,
        d=float(d),
        inlier_ratio=float(best_count / max(1, points.shape[0])),
        inlier_count=best_count,
    )


def intersect_pixels_with_plane(
    pixels_xy: np.ndarray,
    plane: RoadPlane,
    calibration: dict[str, np.ndarray],
) -> np.ndarray:
    intr = camera_intrinsics(calibration)
    if intr is None or pixels_xy.size == 0:
        return np.empty((0, 3), dtype=np.float32)
    fx, fy, cx, cy = intr
    uv = pixels_xy.astype(np.float32)
    rays = np.column_stack(((uv[:, 0] - cx) / fx, (uv[:, 1] - cy) / fy, np.ones(len(uv), dtype=np.float32)))
    denom = rays @ plane.normal.astype(np.float32)
    valid = np.abs(denom) > 1e-5
    t = np.full(len(uv), np.nan, dtype=np.float32)
    t[valid] = -float(plane.d) / denom[valid]
    valid &= np.isfinite(t) & (t > 0.1) & (t < 120.0)
    points = rays[valid] * t[valid, None]
    return points.astype(np.float32)


def _mask_pixels(mask: np.ndarray, stride: int = 2, max_points: int = 12000) -> np.ndarray:
    ys, xs = np.where(mask[::stride, ::stride] > 0)
    if xs.size == 0:
        return np.empty((0, 2), dtype=np.float32)
    pixels = np.column_stack((xs * stride, ys * stride)).astype(np.float32)
    if pixels.shape[0] > max_points:
        step = max(1, pixels.shape[0] // max_points)
        pixels = pixels[::step][:max_points]
    return pixels


def _polyfit_centerline(points_xz: np.ndarray, lane_width_m: float) -> tuple[np.ndarray, float, str]:
    if points_xz.shape[0] < 80:
        return np.asarray([0.0, 0.0], dtype=np.float32), 0.20, "not enough ground-mask support"
    z = points_xz[:, 1]
    x = points_xz[:, 0]
    valid = np.isfinite(x) & np.isfinite(z) & (z >= 3.0) & (z <= 45.0) & (np.abs(x) < 10.0)
    x, z = x[valid], z[valid]
    centers: list[tuple[float, float]] = []
    for z0 in np.arange(4.0, 36.0, 2.0):
        sel = (z >= z0) & (z < z0 + 2.0)
        if int(sel.sum()) < 30:
            continue
        left = float(np.percentile(x[sel], 8))
        right = float(np.percentile(x[sel], 92))
        width = right - left
        if 2.2 <= width <= 7.0:
            centers.append((z0 + 1.0, (left + right) / 2.0))
    if len(centers) < 3:
        return np.asarray([0.0, 0.0], dtype=np.float32), 0.28, "weak centerline support"
    zc = np.asarray([item[0] for item in centers], dtype=np.float32)
    xc = np.asarray([item[1] for item in centers], dtype=np.float32)
    coeff = np.polyfit(zc, xc, deg=1).astype(np.float32)
    residual = float(np.median(np.abs(np.polyval(coeff, zc) - xc)))
    confidence = float(np.clip(0.85 - residual / max(lane_width_m, 1e-6), 0.25, 0.92))
    return coeff, confidence, f"road-mask centerline bins={len(centers)} residual={residual:.2f}m"


def _hough_lane_evidence_mask(image: np.ndarray, support_mask: np.ndarray, lane_color_mask: np.ndarray) -> np.ndarray:
    """Kaggle-style Canny + ROI + Hough evidence, kept as observed markings only."""
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    edges = cv2.bitwise_and(edges, support_mask)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=max(18, w // 24),
        minLineLength=max(18, w // 26),
        maxLineGap=max(20, w // 24),
    )
    hough_mask = np.zeros((h, w), dtype=np.uint8)
    if lines is None:
        return hough_mask
    for raw in np.asarray(lines).reshape(-1, 4):
        x1, y1, x2, y2 = [int(v) for v in raw]
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < max(16, w * 0.025) or dx == 0:
            continue
        slope = dy / dx
        # Ignore horizontal texture/building edges and near-vertical poles.
        if abs(slope) < 0.22 or abs(slope) > 6.0:
            continue
        if max(y1, y2) < int(0.44 * h):
            continue
        segment_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.line(segment_mask, (x1, y1), (x2, y2), 255, max(3, w // 180), cv2.LINE_AA)
        segment_pixels = int(np.count_nonzero(segment_mask))
        if segment_pixels == 0:
            continue
        color_overlap = int(np.count_nonzero(cv2.bitwise_and(segment_mask, lane_color_mask)))
        # Plain Kaggle/Hough accepts any strong edge; for traffic scenes that
        # includes cars, cyclists, poles, and shadows. Keep only line-colored
        # evidence so Hough boosts lane markings rather than object contours.
        if color_overlap / segment_pixels < 0.18:
            continue
        cv2.line(hough_mask, (x1, y1), (x2, y2), 255, max(3, w // 170), cv2.LINE_AA)
    hough_mask = cv2.bitwise_and(hough_mask, support_mask)
    return cv2.dilate(hough_mask, np.ones((3, 3), np.uint8), iterations=1)


def detections_ignore_mask(
    image_shape: tuple[int, int, int],
    detections: list[Detection],
    pad_px: int = 10,
) -> np.ndarray:
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    for det in detections:
        x1, y1, x2, y2 = [int(round(v)) for v in det.bbox]
        if x2 <= x1 or y2 <= y1:
            continue
        x1 = max(0, x1 - pad_px)
        y1 = max(0, y1 - pad_px)
        x2 = min(w - 1, x2 + pad_px)
        y2 = min(h - 1, y2 + pad_px)
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    return mask


def lane_marking_evidence_mask(
    image: np.ndarray,
    road_mask: np.ndarray | None = None,
    ignore_mask: np.ndarray | None = None,
) -> np.ndarray:
    h, w = image.shape[:2]
    hls = cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    hue, lightness, saturation = cv2.split(hls)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    sobel = cv2.convertScaleAbs(np.maximum(np.abs(sobel_x), 0.45 * np.abs(sobel_y)))

    white = ((lightness > 155) & (saturation < 105)).astype(np.uint8) * 255
    yellow = ((hue >= 12) & (hue <= 42) & (saturation > 65) & (lightness > 70)).astype(np.uint8) * 255
    hough_white = ((lightness > 118) & (saturation < 135)).astype(np.uint8) * 255
    hough_yellow = ((hue >= 10) & (hue <= 45) & (saturation > 45) & (lightness > 55)).astype(np.uint8) * 255
    edge = ((sobel > 42) & (sobel < 230)).astype(np.uint8) * 255
    evidence = cv2.bitwise_or(cv2.bitwise_and(cv2.bitwise_or(white, yellow), edge), yellow)

    if road_mask is None:
        support = default_road_roi(image.shape)
    else:
        support = cv2.dilate(
            cv2.resize(road_mask, (w, h), interpolation=cv2.INTER_NEAREST),
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)),
            iterations=1,
        )
    if ignore_mask is not None:
        ignore_mask = cv2.resize(ignore_mask, (w, h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
        support = cv2.bitwise_and(support, cv2.bitwise_not(ignore_mask))
    evidence = cv2.bitwise_and(evidence, support)
    hough_color = cv2.bitwise_and(cv2.bitwise_or(hough_white, hough_yellow), support)
    hough_evidence = _hough_lane_evidence_mask(image, support, hough_color)
    evidence = cv2.bitwise_or(evidence, hough_evidence)
    evidence[: int(0.42 * h), :] = 0
    evidence = cv2.morphologyEx(evidence, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    evidence = cv2.morphologyEx(evidence, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return evidence


def _fit_centerline_from_lane_evidence(
    points_xz: np.ndarray,
    lane_width_m: float,
) -> tuple[np.ndarray, float, str]:
    if points_xz.shape[0] < 80:
        return np.asarray([0.0, 0.0], dtype=np.float32), 0.0, "lane-evidence weak: not enough points"
    z = points_xz[:, 1]
    x = points_xz[:, 0]
    valid = np.isfinite(x) & np.isfinite(z) & (z >= 3.0) & (z <= 42.0) & (np.abs(x) < 8.5)
    x, z = x[valid], z[valid]
    centers: list[tuple[float, float]] = []
    modes: list[str] = []
    for z0 in np.arange(4.0, 36.0, 2.0):
        sel = (z >= z0) & (z < z0 + 2.0)
        if int(sel.sum()) < 10:
            continue
        xs = x[sel]
        left = xs[xs < -0.25]
        right = xs[xs > 0.25]
        center = xs[np.abs(xs) <= 0.35]
        if left.size >= 8 and right.size >= 8:
            left_edge = float(np.percentile(left, 85))
            right_edge = float(np.percentile(right, 15))
            width = right_edge - left_edge
            if 2.3 <= width <= 5.8:
                centers.append((z0 + 1.0, (left_edge + right_edge) / 2.0))
                modes.append("pair")
                continue
        if center.size >= 8:
            centers.append((z0 + 1.0, float(np.median(center))))
            modes.append("center")
            continue
        if left.size >= 10:
            centers.append((z0 + 1.0, float(np.percentile(left, 85) + lane_width_m / 2.0)))
            modes.append("left")
            continue
        if right.size >= 10:
            centers.append((z0 + 1.0, float(np.percentile(right, 15) - lane_width_m / 2.0)))
            modes.append("right")
    if len(centers) < 4:
        return np.asarray([0.0, 0.0], dtype=np.float32), 0.0, f"lane-evidence weak: bins={len(centers)}"

    zc = np.asarray([item[0] for item in centers], dtype=np.float32)
    xc = np.asarray([item[1] for item in centers], dtype=np.float32)
    degree = 2 if len(centers) >= 5 and float(zc.max() - zc.min()) >= 6.0 else 1
    coeff = np.polyfit(zc, xc, deg=degree).astype(np.float32)
    predicted = np.polyval(coeff, zc)
    residual = float(np.median(np.abs(predicted - xc)))
    z_span = float(zc.max() - zc.min())
    support_score = min(1.0, len(centers) / 10.0)
    span_score = min(1.0, z_span / 24.0)
    residual_score = 1.0 - min(1.0, residual / 1.2)
    confidence = float(np.clip(0.25 + 0.30 * support_score + 0.25 * span_score + 0.20 * residual_score, 0.0, 0.90))
    mode_summary = ",".join(sorted(set(modes)))
    return coeff, confidence, f"lane-evidence poly{degree} bins={len(centers)} span={z_span:.1f}m residual={residual:.2f}m modes={mode_summary}"


def _fit_boundary_poly(z_values: list[float], x_values: list[float]) -> tuple[np.ndarray, float, float, str] | None:
    if len(z_values) < 4:
        return None
    zc = np.asarray(z_values, dtype=np.float32)
    xc = np.asarray(x_values, dtype=np.float32)
    span = float(zc.max() - zc.min())
    degree = 2 if len(z_values) >= 5 and span >= 8.0 else 1
    coeff = np.polyfit(zc, xc, deg=degree).astype(np.float32)
    residual = float(np.median(np.abs(np.polyval(coeff, zc) - xc)))
    if residual > 0.75:
        return None
    support_score = min(1.0, len(z_values) / 10.0)
    span_score = min(1.0, span / 24.0)
    residual_score = 1.0 - min(1.0, residual / 0.75)
    confidence = float(np.clip(0.28 + 0.32 * support_score + 0.25 * span_score + 0.15 * residual_score, 0.0, 0.92))
    return coeff, confidence, float(zc.max()), f"poly{degree} bins={len(z_values)} span={span:.1f}m residual={residual:.2f}m"


def _fit_boundaries_from_lane_evidence(
    points_xz: np.ndarray,
    lane_width_m: float,
    road_coeff: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float, str] | None:
    if points_xz.shape[0] < 80:
        return None
    z = points_xz[:, 1]
    x = points_xz[:, 0]
    valid = np.isfinite(x) & np.isfinite(z) & (z >= 2.5) & (z <= 42.0) & (np.abs(x) < 9.0)
    x, z = x[valid], z[valid]
    if x.size < 80:
        return None
    left_z: list[float] = []
    left_x: list[float] = []
    right_z: list[float] = []
    right_x: list[float] = []
    center_z: list[float] = []
    center_x: list[float] = []
    for z0 in np.arange(3.0, 36.0, 2.0):
        sel = (z >= z0) & (z < z0 + 2.0)
        if int(sel.sum()) < 8:
            continue
        xs = x[sel]
        road_center = float(np.polyval(road_coeff, z0 + 1.0))
        relative = xs - road_center
        left = xs[(relative >= -3.2) & (relative <= -0.35)]
        right = xs[(relative >= 0.35) & (relative <= 3.2)]
        center = xs[np.abs(relative) < 0.35]
        if left.size >= 6:
            left_z.append(float(z0 + 1.0))
            left_x.append(float(np.percentile(left, 75)))
        if right.size >= 6:
            right_z.append(float(z0 + 1.0))
            right_x.append(float(np.percentile(right, 25)))
        if center.size >= 6:
            center_z.append(float(z0 + 1.0))
            center_x.append(float(np.median(center)))

    candidates: list[tuple[str, np.ndarray, np.ndarray, float, float, str]] = []
    left_fit = _fit_boundary_poly(left_z, left_x)
    right_fit = _fit_boundary_poly(right_z, right_x)
    if left_fit is not None and right_fit is not None:
        left_coeff_pair, left_confidence, left_z_max, left_note = left_fit
        right_coeff_pair, right_confidence, right_z_max, right_note = right_fit
        z_max_pair = min(left_z_max, right_z_max)
        zs_pair = np.linspace(4.0, max(8.0, min(z_max_pair, 30.0)), 6, dtype=np.float32)
        widths = np.polyval(right_coeff_pair, zs_pair) - np.polyval(left_coeff_pair, zs_pair)
        finite_widths = widths[np.isfinite(widths)]
        if finite_widths.size >= 4:
            median_width = float(np.median(finite_widths))
            width_spread = float(np.percentile(finite_widths, 90) - np.percentile(finite_widths, 10))
            if 2.35 <= median_width <= 5.55 and width_spread <= 1.35:
                pair_confidence = min(left_confidence, right_confidence) + 0.08
                pair_note = (
                    f"pair left={left_note} right={right_note} "
                    f"width={median_width:.2f}m spread={width_spread:.2f}m"
                )
                candidates.append(
                    (
                        "pair",
                        left_coeff_pair,
                        right_coeff_pair,
                        float(np.clip(pair_confidence, 0.0, 0.94)),
                        z_max_pair,
                        pair_note,
                    )
                )
    if left_fit is not None:
        left_coeff, confidence, z_max, note = left_fit
        right_coeff = left_coeff.copy()
        right_coeff[-1] += lane_width_m
        candidates.append(("left", left_coeff, right_coeff, confidence, z_max, note))
    if right_fit is not None:
        right_coeff, confidence, z_max, note = right_fit
        left_coeff = right_coeff.copy()
        left_coeff[-1] -= lane_width_m
        candidates.append(("right", left_coeff, right_coeff, confidence, z_max, note))
    center_fit = _fit_boundary_poly(center_z, center_x)
    if center_fit is not None:
        center_coeff, confidence, z_max, note = center_fit
        left_coeff = center_coeff.copy()
        right_coeff = center_coeff.copy()
        left_coeff[-1] -= lane_width_m / 2.0
        right_coeff[-1] += lane_width_m / 2.0
        candidates.append(("center", left_coeff, right_coeff, confidence * 0.9, z_max, note))
    if not candidates:
        return None

    def boundary_diverges_from_road(side: str, left_coeff: np.ndarray, right_coeff: np.ndarray) -> bool:
        if side not in ("left", "right"):
            return False
        zs_check = np.asarray([4.0, 8.0, 12.0, 16.0], dtype=np.float32)
        boundary = np.polyval(left_coeff if side == "left" else right_coeff, zs_check)
        road = np.polyval(road_coeff, zs_check)
        rel = np.asarray(boundary - road, dtype=np.float32)
        finite = np.isfinite(rel)
        if int(finite.sum()) < 3:
            return True
        rel = rel[finite]
        # A single visible boundary is safe only when it stays near the ego
        # lane side. If it moves farther away, it is likely an adjacent lane
        # divider and should not be shifted across the ego lane.
        if side == "left":
            return bool(float(rel[-1] - rel[0]) < -0.55)
        return bool(float(rel[-1] - rel[0]) > 0.55)

    filtered_candidates: list[tuple[str, np.ndarray, np.ndarray, float, float, str]] = []
    for item in candidates:
        side, left_coeff_item, right_coeff_item, confidence_item, z_max_item, note_item = item
        if boundary_diverges_from_road(side, left_coeff_item, right_coeff_item):
            continue
        filtered_candidates.append(item)
    candidates = filtered_candidates
    if not candidates:
        return None

    def candidate_score(item: tuple[str, np.ndarray, np.ndarray, float, float, str]) -> float:
        side, left_coeff, right_coeff, confidence, _, _ = item
        zs = np.asarray([4.0, 8.0, 12.0, 18.0, 26.0], dtype=np.float32)
        center = (np.polyval(left_coeff, zs) + np.polyval(right_coeff, zs)) / 2.0
        road = np.polyval(road_coeff, zs)
        drift = float(np.median(np.abs(center - road)))
        side_bonus = 0.16 if side == "pair" else (0.08 if side in ("left", "right") else 0.0)
        return confidence + side_bonus - 0.18 * drift

    side, left_coeff, right_coeff, confidence, z_max, note = max(candidates, key=candidate_score)
    zs = np.asarray([4.0, 8.0, 12.0, 18.0, 26.0], dtype=np.float32)
    center = (np.polyval(left_coeff, zs) + np.polyval(right_coeff, zs)) / 2.0
    # A boundary fitted from paint is already expressed in camera-ground
    # coordinates.  Do not translate it towards the road ROI centre: the ROI
    # is only a support region and its centre is not a lane measurement.  That
    # translation was the reason curved lanes could be visibly detached from
    # their painted markings (notably T01-Sample frame 000300).
    anchor = 0.0
    center_after = (np.polyval(left_coeff, zs) + np.polyval(right_coeff, zs)) / 2.0
    road_after = np.polyval(road_coeff, zs)
    drift_after = np.asarray(center_after - road_after, dtype=np.float32)
    near_mid_drift = float(np.max(np.abs(drift_after[:3])))
    far_drift = float(np.max(np.abs(drift_after)))
    if near_mid_drift > 0.55 or far_drift > 0.95:
        return None
    confidence = float(np.clip(confidence, 0.0, 0.9))
    if side == "pair":
        label = "paired-boundary"
    elif side == "center":
        label = "centerline-boundary"
    else:
        label = f"single-boundary {side}"
    return left_coeff, right_coeff, confidence, z_max, f"{label} {note} anchor={anchor:+.2f}m"


def _project_plane_point(
    x_m: float,
    z_m: float,
    plane: RoadPlane,
    calibration: dict[str, np.ndarray],
) -> tuple[int, int] | None:
    intr = camera_intrinsics(calibration)
    if intr is None or abs(float(plane.normal[1])) < 1e-5:
        return None
    fx, fy, cx, cy = intr
    y_m = -(float(plane.normal[0]) * x_m + float(plane.normal[2]) * z_m + plane.d) / float(plane.normal[1])
    if z_m <= 0.1:
        return None
    u = fx * x_m / z_m + cx
    v = fy * y_m / z_m + cy
    if not (math.isfinite(u) and math.isfinite(v)):
        return None
    return int(round(u)), int(round(v))


def _near_z_from_bottom_ray(
    image_shape: tuple[int, int, int],
    plane: RoadPlane,
    calibration: dict[str, np.ndarray],
    fallback_z_m: float = 2.4,
) -> float:
    intr = camera_intrinsics(calibration)
    if intr is None:
        return fallback_z_m
    _, fy, _, cy = intr
    h = image_shape[0]
    ray = np.asarray([0.0, (h - 1 - cy) / fy, 1.0], dtype=np.float32)
    denom = float(ray @ plane.normal.astype(np.float32))
    if abs(denom) < 1e-5:
        return fallback_z_m
    t = -float(plane.d) / denom
    if not math.isfinite(t) or t <= 0:
        return fallback_z_m
    return float(np.clip(t + 0.15, 1.8, 4.0))


def plane_lane_masks_from_boundaries(
    image_shape: tuple[int, int, int],
    left_coeff: np.ndarray,
    right_coeff: np.ndarray,
    plane: RoadPlane,
    calibration: dict[str, np.ndarray],
    z_near_m: float | None = None,
    z_far_m: float = 45.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w = image_shape[:2]
    if z_near_m is None:
        z_near_m = _near_z_from_bottom_ray(image_shape, plane, calibration)
    left_pts: list[tuple[int, int]] = []
    right_pts: list[tuple[int, int]] = []
    center_pts: list[tuple[int, int]] = []
    z_far_m = max(z_near_m + 4.0, z_far_m)
    for z_m in np.linspace(z_far_m, z_near_m, 42):
        left_x = float(np.polyval(left_coeff, z_m))
        right_x = float(np.polyval(right_coeff, z_m))
        center_x = (left_x + right_x) / 2.0
        left = _project_plane_point(left_x, float(z_m), plane, calibration)
        right = _project_plane_point(right_x, float(z_m), plane, calibration)
        center = _project_plane_point(center_x, float(z_m), plane, calibration)
        if left is not None:
            left_pts.append((int(np.clip(left[0], 0, w - 1)), int(np.clip(left[1], 0, h - 1))))
        if right is not None:
            right_pts.append((int(np.clip(right[0], 0, w - 1)), int(np.clip(right[1], 0, h - 1))))
        if center is not None:
            center_pts.append((int(np.clip(center[0], 0, w - 1)), int(np.clip(center[1], 0, h - 1))))
    corridor_mask = np.zeros((h, w), dtype=np.uint8)
    lane_mask = np.zeros((h, w), dtype=np.uint8)
    if len(left_pts) >= 2 and len(right_pts) >= 2:
        polygon = np.asarray([*left_pts, *reversed(right_pts)], dtype=np.int32)
        cv2.fillPoly(corridor_mask, [polygon], 255)
        cv2.polylines(lane_mask, [np.asarray(left_pts, dtype=np.int32)], False, 255, 3, cv2.LINE_AA)
        cv2.polylines(lane_mask, [np.asarray(right_pts, dtype=np.int32)], False, 255, 3, cv2.LINE_AA)
    if len(center_pts) >= 2:
        cv2.polylines(lane_mask, [np.asarray(center_pts, dtype=np.int32)], False, 180, 2, cv2.LINE_AA)
    vertical_mask = vertical_corridor_from_floor_mask(corridor_mask)
    return corridor_mask, vertical_mask, lane_mask


def vertical_corridor_from_floor_mask(corridor_mask: np.ndarray) -> np.ndarray:
    """Extend a floor mask upward so upright obstacles can be lane-filtered."""
    h, w = corridor_mask.shape[:2]
    vertical_mask = np.zeros((h, w), dtype=np.uint8)
    ys, xs = np.where(corridor_mask > 0)
    for x in np.unique(xs):
        column_ys = ys[xs == x]
        if column_ys.size:
            vertical_mask[max(0, int(0.18 * h)) : int(column_ys.max()) + 1, int(x)] = 255
    vertical_mask = cv2.dilate(
        vertical_mask,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(0.018 * w)), 3)),
        iterations=1,
    )
    return vertical_mask


def plane_lane_masks_from_centerline(
    image_shape: tuple[int, int, int],
    center_coeff: np.ndarray,
    plane: RoadPlane,
    calibration: dict[str, np.ndarray],
    lane_width_m: float = 3.7,
    z_near_m: float | None = None,
    z_far_m: float = 45.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    left_coeff = center_coeff.copy()
    right_coeff = center_coeff.copy()
    left_coeff[-1] -= lane_width_m / 2.0
    right_coeff[-1] += lane_width_m / 2.0
    return plane_lane_masks_from_boundaries(
        image_shape,
        left_coeff,
        right_coeff,
        plane,
        calibration,
        z_near_m=z_near_m,
        z_far_m=z_far_m,
    )


def estimate_plane_lane(
    image: np.ndarray,
    depth: np.ndarray | None,
    calibration: dict[str, np.ndarray],
    road_mask: np.ndarray | None = None,
    lane_mask: np.ndarray | None = None,
    ignore_mask: np.ndarray | None = None,
    lane_width_m: float = 3.7,
    lookahead_m: float = 10.0,
    trusted_external_masks: bool = False,
) -> PlaneLaneEstimate:
    h, w = image.shape[:2]
    if road_mask is None:
        road_mask = default_road_roi(image.shape)
        source = "default_roi"
    else:
        road_mask = cv2.resize(road_mask, (w, h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
        source = "ai_or_external_mask"
    if lane_mask is None:
        lane_mask = np.zeros((h, w), dtype=np.uint8)
    else:
        lane_mask = cv2.resize(lane_mask, (w, h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
    plane = fit_road_plane_ransac(depth, calibration, road_mask)
    road_pixels = _mask_pixels(road_mask, stride=2)
    ground_points = intersect_pixels_with_plane(road_pixels, plane, calibration)
    road_coeff, road_confidence, road_note = _polyfit_centerline(
        ground_points[:, [0, 2]] if ground_points.size else ground_points,
        lane_width_m,
    )
    external_lane_mask = np.count_nonzero(lane_mask) > 0
    # Human-authored masks are a ground-truth reference.  Keep their exact
    # pixel geometry for both the floor corridor and visible lane lines.  The
    # plane fit is still used to report metric offset, but must not redraw or
    # shift a line the annotator placed on a road marking.
    if trusted_external_masks and external_lane_mask and np.count_nonzero(road_mask) > 0:
        center_x = float(np.polyval(road_coeff, lookahead_m))
        derivative = float(np.polyval(np.polyder(road_coeff), lookahead_m)) if road_coeff.size > 1 else 0.0
        heading_deg = float(math.degrees(math.atan(derivative)))
        return PlaneLaneEstimate(
            road_mask=road_mask,
            lane_mask=lane_mask,
            corridor_mask=road_mask,
            vertical_corridor_mask=vertical_corridor_from_floor_mask(road_mask),
            lane_offset_m=float(-center_x),
            heading_deg=heading_deg,
            confidence=float(np.clip(max(road_confidence, 0.92), 0.0, 0.98)),
            plane=plane,
            source="trusted_external_masks",
            note=f"authoritative external masks; plane={road_note}",
        )
    lane_evidence = lane_mask if external_lane_mask else lane_marking_evidence_mask(image, road_mask, ignore_mask)
    lane_pixels = _mask_pixels(lane_evidence, stride=1, max_points=16000)
    lane_points = intersect_pixels_with_plane(lane_pixels, plane, calibration)
    boundary_fit = _fit_boundaries_from_lane_evidence(
        lane_points[:, [0, 2]] if lane_points.size else lane_points,
        lane_width_m,
        road_coeff,
    )
    use_boundary = boundary_fit is not None and (external_lane_mask or boundary_fit[2] >= road_confidence - 0.18)
    if use_boundary and boundary_fit is not None:
        left_coeff, right_coeff, boundary_confidence, boundary_z_max, boundary_note = boundary_fit
        center_coeff = (left_coeff + right_coeff) / 2.0
        boundary_center_x = float(np.polyval(center_coeff, lookahead_m))
        boundary_derivative = float(np.polyval(np.polyder(center_coeff), lookahead_m)) if center_coeff.size > 1 else 0.0
        boundary_heading = float(math.degrees(math.atan(boundary_derivative)))
        if abs(boundary_center_x) <= 0.75 and abs(boundary_heading) <= 7.5:
            coeff = center_coeff
            confidence = max(boundary_confidence, min(0.88, road_confidence + 0.01))
            note = f"{boundary_note}; plane={road_note}"
            corridor_mask, vertical_mask, projected_lane_mask = plane_lane_masks_from_boundaries(
                image.shape,
                left_coeff,
                right_coeff,
                plane,
                calibration,
                z_far_m=float(np.clip(boundary_z_max + 4.0, 16.0, 36.0)),
            )
        else:
            coeff = road_coeff
            confidence = road_confidence
            note = (
                f"{road_note}; single-boundary rejected "
                f"offset={-boundary_center_x:+.2f}m heading={boundary_heading:+.2f}deg; {boundary_note}"
            )
            corridor_mask, vertical_mask, projected_lane_mask = plane_lane_masks_from_centerline(
                image.shape,
                coeff,
                plane,
                calibration,
                lane_width_m=lane_width_m,
            )
    else:
        coeff = road_coeff
        confidence = road_confidence
        note = f"{road_note}; single-boundary weak"
        corridor_mask, vertical_mask, projected_lane_mask = plane_lane_masks_from_centerline(
            image.shape,
            coeff,
            plane,
            calibration,
            lane_width_m=lane_width_m,
        )
    center_x = float(np.polyval(coeff, lookahead_m))
    derivative = float(np.polyval(np.polyder(coeff), lookahead_m)) if coeff.size > 1 else 0.0
    heading_deg = float(math.degrees(math.atan(derivative)))
    lane_offset_m = -center_x
    if external_lane_mask:
        projected_lane_mask = cv2.bitwise_or(projected_lane_mask, lane_mask)
        confidence = float(np.clip(confidence + 0.05, 0.0, 0.96))
    if plane.source == "flat_ground_fallback":
        confidence = min(confidence, 0.42)
    return PlaneLaneEstimate(
        road_mask=road_mask,
        lane_mask=projected_lane_mask,
        corridor_mask=corridor_mask,
        vertical_corridor_mask=vertical_mask,
        lane_offset_m=float(lane_offset_m),
        heading_deg=heading_deg,
        confidence=confidence,
        plane=plane,
        source=source,
        note=note,
    )


def compute_road_and_lane(
    image: np.ndarray, lane_width_m: float = 3.7
) -> tuple[np.ndarray, np.ndarray, float, list[tuple[int, int, int, int]]]:
    h, w = image.shape[:2]
    road_mask = np.zeros((h, w), dtype=np.uint8)
    polygon = np.array(
        [[int(0.08 * w), h - 1], [int(0.44 * w), int(0.52 * h)],
         [int(0.56 * w), int(0.52 * h)], [int(0.92 * w), h - 1]],
        dtype=np.int32,
    )
    cv2.fillPoly(road_mask, [polygon], 255)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 160)
    edges = cv2.bitwise_and(edges, road_mask)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=35,
        minLineLength=max(30, w // 14),
        maxLineGap=35,
    )
    lane_mask = np.zeros((h, w), dtype=np.uint8)
    line_segments: list[tuple[int, int, int, int]] = []
    left_x: list[float] = []
    right_x: list[float] = []
    y_bottom = h - 1
    raw_lines = [] if lines is None else np.asarray(lines).reshape(-1, 4)
    for raw in raw_lines:
        x1, y1, x2, y2 = [int(v) for v in raw]
        if x2 == x1:
            continue
        slope = (y2 - y1) / (x2 - x1)
        if abs(slope) < 0.35:
            continue
        b = y1 - slope * x1
        x_at_bottom = (y_bottom - b) / slope
        if not (0 <= x_at_bottom <= w):
            continue
        line_segments.append((x1, y1, x2, y2))
        cv2.line(lane_mask, (x1, y1), (x2, y2), 255, 3, cv2.LINE_AA)
        if slope < 0 and x_at_bottom < w * 0.62:
            left_x.append(float(x_at_bottom))
        elif slope > 0 and x_at_bottom > w * 0.38:
            right_x.append(float(x_at_bottom))

    if left_x and right_x:
        lane_left = float(np.median(left_x))
        lane_right = float(np.median(right_x))
        lane_center = (lane_left + lane_right) / 2.0
        px_per_m = max(abs(lane_right - lane_left) / lane_width_m, 1.0)
        lane_offset_m = float((w / 2.0 - lane_center) / px_per_m)
    else:
        lane_offset_m = math.nan
    return road_mask, lane_mask, lane_offset_m, line_segments


def _line_x_at_y(segment: tuple[int, int, int, int], y_value: float) -> float | None:
    x1, y1, x2, y2 = segment
    if x2 == x1:
        return None
    slope = (y2 - y1) / (x2 - x1)
    if abs(slope) < 1e-6:
        return None
    intercept = y1 - slope * x1
    return float((y_value - intercept) / slope)


def build_lane_corridor_masks(
    image_shape: tuple[int, int, int],
    line_segments: list[tuple[int, int, int, int]],
    lane_width_m: float = 3.7,
) -> tuple[np.ndarray, np.ndarray]:
    """Build an ego-lane floor mask and its vertical risk prism.

    The floor mask is the drivable corridor at road level. The vertical mask
    extends each lane column upward, so objects standing on that lane are still
    accepted even when most of their bbox is above the road surface.
    """
    h, w = image_shape[:2]
    y_bottom = h - 1
    y_top = int(0.52 * h)
    left_bottom: list[float] = []
    left_top: list[float] = []
    right_bottom: list[float] = []
    right_top: list[float] = []
    for segment in line_segments:
        x1, y1, x2, y2 = segment
        if x2 == x1:
            continue
        slope = (y2 - y1) / (x2 - x1)
        xb = _line_x_at_y(segment, y_bottom)
        xt = _line_x_at_y(segment, y_top)
        if xb is None or xt is None:
            continue
        if not (-0.25 * w <= xb <= 1.25 * w and -0.25 * w <= xt <= 1.25 * w):
            continue
        if slope < 0 and xb < w * 0.65:
            left_bottom.append(xb)
            left_top.append(xt)
        elif slope > 0 and xb > w * 0.35:
            right_bottom.append(xb)
            right_top.append(xt)

    if left_bottom and right_bottom:
        lb, lt = float(np.median(left_bottom)), float(np.median(left_top))
        rb, rt = float(np.median(right_bottom)), float(np.median(right_top))
    else:
        # Conservative ego-lane fallback; narrower than the full road trapezoid.
        lb, rb = 0.30 * w, 0.70 * w
        lt, rt = 0.46 * w, 0.54 * w

    if rb - lb < w * 0.12:
        center_b = (lb + rb) / 2.0
        center_t = (lt + rt) / 2.0
        lb, rb = center_b - 0.20 * w, center_b + 0.20 * w
        lt, rt = center_t - 0.05 * w, center_t + 0.05 * w

    floor_mask = np.zeros((h, w), dtype=np.uint8)
    polygon = np.array(
        [
            [int(np.clip(lb, 0, w - 1)), y_bottom],
            [int(np.clip(lt, 0, w - 1)), y_top],
            [int(np.clip(rt, 0, w - 1)), y_top],
            [int(np.clip(rb, 0, w - 1)), y_bottom],
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(floor_mask, [polygon], 255)

    vertical_mask = np.zeros((h, w), dtype=np.uint8)
    ys, xs = np.where(floor_mask > 0)
    for x in np.unique(xs):
        column_ys = ys[xs == x]
        if column_ys.size == 0:
            continue
        y_max = int(column_ys.max())
        y_min = max(0, int(0.18 * h))
        vertical_mask[y_min : y_max + 1, int(x)] = 255
    kernel_w = max(3, int(0.018 * w))
    vertical_mask = cv2.dilate(
        vertical_mask,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 3)),
        iterations=1,
    )
    return floor_mask, vertical_mask


def detection_in_lane_corridor(
    det: Detection,
    floor_mask: np.ndarray,
    vertical_mask: np.ndarray | None = None,
    lane_half_width_m: float = 1.85,
    lateral_margin_m: float = 0.25,
) -> bool:
    if math.isfinite(det.lateral_m):
        return abs(det.lateral_m) <= lane_half_width_m + lateral_margin_m
    if det.location is not None and det.location[2] > 0.1:
        return abs(float(det.location[0])) <= lane_half_width_m + lateral_margin_m
    h, w = floor_mask.shape[:2]
    x1, y1, x2, y2 = det.bbox
    foot_x = int(np.clip((x1 + x2) / 2.0, 0, w - 1))
    foot_y = int(np.clip(y2 - 1, 0, h - 1))
    if floor_mask[foot_y, foot_x] > 0:
        return True
    if vertical_mask is not None:
        center_x = int(np.clip((x1 + x2) / 2.0, 0, w - 1))
        center_y = int(np.clip((y1 + y2) / 2.0, 0, h - 1))
        return bool(vertical_mask[center_y, center_x] > 0)
    return False


def filter_detections_by_lane_corridor(
    detections: list[Detection],
    floor_mask: np.ndarray,
    vertical_mask: np.ndarray | None = None,
    lane_half_width_m: float = 1.85,
    lateral_margin_m: float = 0.25,
) -> list[Detection]:
    return [
        det
        for det in detections
        if detection_in_lane_corridor(
            det,
            floor_mask,
            vertical_mask,
            lane_half_width_m=lane_half_width_m,
            lateral_margin_m=lateral_margin_m,
        )
    ]


def iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return 0.0 if union <= 0 else float(inter / union)


class SimpleTracker:
    def __init__(self, max_missed: int = 10, iou_threshold: float = 0.08) -> None:
        self.max_missed = max_missed
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.tracks: dict[int, TrackState] = {}

    def update(self, detections: list[Detection], timestamp: float) -> list[Detection]:
        unmatched_tracks = set(self.tracks)
        for det in sorted(detections, key=lambda d: d.bbox[2] - d.bbox[0], reverse=True):
            best_id: int | None = None
            best_score = 0.0
            for track_id in list(unmatched_tracks):
                track = self.tracks[track_id]
                if track.object_type != det.object_type:
                    continue
                score = iou(track.bbox, det.bbox)
                if score > best_score:
                    best_id = track_id
                    best_score = score
            if best_id is None or best_score < self.iou_threshold:
                best_id = self.next_id
                self.next_id += 1
            else:
                unmatched_tracks.discard(best_id)
            self._attach_motion(det, best_id, timestamp)

        for track_id in list(unmatched_tracks):
            track = self.tracks[track_id]
            track.missed += 1
            if track.missed > self.max_missed:
                del self.tracks[track_id]
        return detections

    def _attach_motion(self, det: Detection, track_id: int, timestamp: float) -> None:
        prev = self.tracks.get(track_id)
        det.track_id = track_id
        if prev is not None and math.isfinite(prev.distance_m) and math.isfinite(det.distance_m):
            dt = max(timestamp - prev.timestamp, 1e-6)
            closing_speed = (prev.distance_m - det.distance_m) / dt
            det.relative_speed_mps = float(closing_speed)
            det.ttc_s = (
                float(det.distance_m / closing_speed)
                if closing_speed > 0.25 and det.distance_m > 0
                else math.inf
            )
            history = [*prev.history[-4:], (timestamp, det.distance_m)]
        else:
            history = [(timestamp, det.distance_m)]
        self.tracks[track_id] = TrackState(
            track_id=track_id,
            object_type=det.object_type,
            bbox=det.bbox,
            timestamp=timestamp,
            distance_m=det.distance_m,
            history=history,
        )


def safe_float(value: Any, default: float = math.nan) -> float:
    if value in (None, "Infinity", "-Infinity"):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def finite_or_none(value: float) -> float | str | None:
    if value is None or not math.isfinite(value):
        return "inf" if value == math.inf else None
    return round(float(value), 4)


def draw_overlay(
    image: np.ndarray,
    detections: list[Detection],
    road_mask: np.ndarray | None,
    lane_mask: np.ndarray | None,
    lane_offset_m: float,
    line_segments: list[tuple[int, int, int, int]] | None = None,
    corridor_mask: np.ndarray | None = None,
    vertical_corridor_mask: np.ndarray | None = None,
) -> np.ndarray:
    output = image.copy()
    if road_mask is not None:
        road_color = np.zeros_like(output)
        road_color[:, :, 1] = 150
        output = np.where(road_mask[:, :, None] > 0, cv2.addWeighted(output, 0.82, road_color, 0.18, 0), output)
    if vertical_corridor_mask is not None:
        prism_color = np.zeros_like(output)
        prism_color[:, :, 0] = 180
        output = np.where(vertical_corridor_mask[:, :, None] > 0, cv2.addWeighted(output, 0.92, prism_color, 0.08, 0), output)
    if corridor_mask is not None:
        corridor_color = np.zeros_like(output)
        corridor_color[:, :, 0] = 220
        corridor_color[:, :, 1] = 180
        output = np.where(corridor_mask[:, :, None] > 0, cv2.addWeighted(output, 0.72, corridor_color, 0.28, 0), output)
    if lane_mask is not None:
        lane_color = np.zeros_like(output)
        lane_color[:, :, 2] = 255
        lane_color[:, :, 1] = 210
        output = np.where(lane_mask[:, :, None] > 0, lane_color, output)
    for segment in line_segments or []:
        cv2.line(output, segment[:2], segment[2:], (30, 220, 255), 2, cv2.LINE_AA)
    for det in detections:
        color = CLASS_COLORS.get(det.object_type, (220, 220, 220))
        x1, y1, x2, y2 = [int(round(v)) for v in det.bbox]
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        ttc_text = "inf" if not math.isfinite(det.ttc_s) else f"{det.ttc_s:.1f}s"
        dist_text = "--" if not math.isfinite(det.distance_m) else f"{det.distance_m:.1f}m"
        rel_text = "--" if not math.isfinite(det.relative_speed_mps) else f"{det.relative_speed_mps:+.1f}m/s"
        label = f"#{det.track_id or 0} {det.object_type} {dist_text} rel {rel_text} TTC {ttc_text}"
        draw_tag(output, label, (x1, max(16, y1 - 5)), color)
    offset_text = "--" if not math.isfinite(lane_offset_m) else f"{lane_offset_m:+.2f} m"
    draw_tag(output, f"lane offset {offset_text}", (14, 28), (30, 220, 255))
    return output


def draw_tag(
    image: np.ndarray,
    text: str,
    anchor: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    x, y = anchor
    size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.46, 1)[0]
    x = int(np.clip(x, 0, max(0, image.shape[1] - size[0] - 8)))
    y = int(np.clip(y, size[1] + 8, image.shape[0] - 2))
    cv2.rectangle(image, (x, y - size[1] - 8), (x + size[0] + 8, y + 4), color, -1)
    cv2.putText(
        image,
        text,
        (x + 4, y - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (15, 20, 25),
        1,
        cv2.LINE_AA,
    )
