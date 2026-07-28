"""Projection, camera geometry, and road-plane estimation."""

from __future__ import annotations

import math
from collections.abc import Iterable

import cv2
import numpy as np
from fleetiq_data import Calibration, KittiObject

from .types import Detection, RoadPlane


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


def valid_bbox(
    bbox: Iterable[float],
    width: int,
    height: int,
    min_size: float = 3.0,
) -> tuple[float, float, float, float] | None:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    x1 = float(np.clip(x1, 0, width - 1))
    x2 = float(np.clip(x2, 0, width - 1))
    y1 = float(np.clip(y1, 0, height - 1))
    y2 = float(np.clip(y2, 0, height - 1))
    if x2 - x1 < min_size or y2 - y1 < min_size:
        return None
    return x1, y1, x2, y2


def bbox_from_projected_object(
    obj: KittiObject,
    projection: np.ndarray,
    width: int,
    height: int,
) -> tuple[float, float, float, float] | None:
    corners = box_3d_corners(obj)
    if corners is None:
        return valid_bbox(obj.bbox, width, height)
    points = project_points(corners, projection)
    if points is None:
        return valid_bbox(obj.bbox, width, height)
    return valid_bbox(
        (
            float(np.min(points[:, 0])),
            float(np.min(points[:, 1])),
            float(np.max(points[:, 0])),
            float(np.max(points[:, 1])),
        ),
        width,
        height,
    )


def default_road_roi(shape: tuple[int, ...]) -> np.ndarray:
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
    calibration: Calibration,
    mask: np.ndarray | None = None,
    max_points: int = 8000,
) -> np.ndarray:
    h, w = depth.shape[:2]
    yy, xx = np.indices((h, w))
    z = depth.astype(np.float32)
    valid = np.isfinite(z) & (z > 1.0) & (z < 80.0)
    support = (
        default_road_roi((h, w))
        if mask is None
        else cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    )
    valid &= support > 0
    x = (xx.astype(np.float32) - calibration.cx) * z / calibration.fx
    y = (yy.astype(np.float32) - calibration.cy) * z / calibration.fy
    valid &= (y > 0.4) & (y < 3.2)
    points = np.column_stack((x[valid], y[valid], z[valid])).astype(np.float32)
    if points.shape[0] > max_points:
        step = max(1, points.shape[0] // max_points)
        points = points[::step][:max_points]
    return points


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
    calibration: Calibration,
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
        inliers = np.abs(points @ normal + d) < threshold_m
        count = int(inliers.sum())
        if count > best_count:
            best_count = count
            best_inliers = inliers
    if best_inliers is None or best_count < min_points:
        return fallback_road_plane()
    inlier_points = points[best_inliers]
    centroid = inlier_points.mean(axis=0)
    _, _, vh = np.linalg.svd(inlier_points - centroid, full_matrices=False)
    normal = vh[-1].astype(np.float64)
    norm = float(np.linalg.norm(normal))
    if norm < 1e-9:
        return fallback_road_plane()
    normal /= norm
    if normal[1] < 0:
        normal *= -1.0
    return RoadPlane(
        normal=normal.astype(np.float32),
        d=-float(normal @ centroid),
        inlier_ratio=float(best_count / points.shape[0]),
        inlier_count=best_count,
    )


def intersect_pixels_with_plane(
    pixels_xy: np.ndarray,
    plane: RoadPlane,
    calibration: Calibration,
) -> np.ndarray:
    if pixels_xy.size == 0:
        return np.empty((0, 3), dtype=np.float32)
    uv = pixels_xy.astype(np.float32)
    rays = np.column_stack(
        (
            (uv[:, 0] - calibration.cx) / calibration.fx,
            (uv[:, 1] - calibration.cy) / calibration.fy,
            np.ones(len(uv), dtype=np.float32),
        )
    )
    denom = rays @ plane.normal.astype(np.float32)
    valid = np.abs(denom) > 1e-5
    distance = np.full(len(uv), np.nan, dtype=np.float32)
    distance[valid] = -float(plane.d) / denom[valid]
    valid &= np.isfinite(distance) & (distance > 0.1) & (distance < 120.0)
    return (rays[valid] * distance[valid, None]).astype(np.float32)


def project_ground_point(
    x_m: float,
    z_m: float,
    plane: RoadPlane,
    calibration: Calibration,
) -> tuple[int, int] | None:
    if abs(float(plane.normal[1])) < 1e-5 or z_m <= 0.1:
        return None
    y_m = -(
        float(plane.normal[0]) * x_m + float(plane.normal[2]) * z_m + plane.d
    ) / float(plane.normal[1])
    u = calibration.fx * x_m / z_m + calibration.cx
    v = calibration.fy * y_m / z_m + calibration.cy
    if not (math.isfinite(u) and math.isfinite(v)):
        return None
    return round(u), round(v)


def near_ground_distance(
    image_shape: tuple[int, ...],
    plane: RoadPlane,
    calibration: Calibration,
    fallback_z_m: float = 2.4,
) -> float:
    h = image_shape[0]
    ray = np.asarray(
        [0.0, (h - 1 - calibration.cy) / calibration.fy, 1.0],
        dtype=np.float32,
    )
    denom = float(ray @ plane.normal.astype(np.float32))
    if abs(denom) < 1e-5:
        return fallback_z_m
    distance = -float(plane.d) / denom
    if not math.isfinite(distance) or distance <= 0:
        return fallback_z_m
    return float(np.clip(distance + 0.15, 1.8, 4.0))
