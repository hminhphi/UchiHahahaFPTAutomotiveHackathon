"""Ground-truth, stereo, and object-region distance estimation."""

from __future__ import annotations

from typing import Literal

import cv2
import numpy as np
from fleetiq_data import Calibration, find_frame
from fleetiq_data.trips import TripRecord

from .types import DepthEstimate, Detection


def load_ground_truth_depth(
    trip: TripRecord,
    frame_index: int,
    policy: Literal["exact", "previous", "nearest"] = "previous",
) -> np.ndarray | None:
    """Load sparse depth, with a causal default that never selects the future."""
    path = find_frame(
        trip.depth_dir,
        frame_index,
        suffixes=(".npy",),
        policy=policy,
    )
    if path is None:
        return None
    return np.load(path).astype(np.float32)


def stereo_depth(
    left: np.ndarray,
    right: np.ndarray,
    calibration: Calibration,
    *,
    max_depth_m: float = 90.0,
    num_disparities: int = 128,
    block_size: int = 7,
) -> np.ndarray:
    """Estimate metric depth from a rectified stereo pair."""
    if calibration.fx <= 0.0 or calibration.baseline_m <= 0.0:
        raise ValueError("Stereo depth requires positive focal length and baseline")
    if left.shape[:2] != right.shape[:2]:
        raise ValueError("Stereo images must have matching dimensions")
    if num_disparities <= 0 or num_disparities % 16:
        raise ValueError("num_disparities must be a positive multiple of 16")
    if block_size < 3 or block_size % 2 == 0:
        raise ValueError("block_size must be an odd integer of at least 3")
    gray_left = _grayscale(left)
    gray_right = _grayscale(right)
    matcher = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=num_disparities,
        blockSize=block_size,
        P1=8 * block_size**2,
        P2=32 * block_size**2,
        disp12MaxDiff=1,
        uniquenessRatio=8,
        speckleWindowSize=80,
        speckleRange=24,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
    )
    disparity = matcher.compute(gray_left, gray_right).astype(np.float32) / 16.0
    depth = np.full(disparity.shape, np.nan, dtype=np.float32)
    valid = disparity > 0.5
    depth[valid] = calibration.fx * calibration.baseline_m / disparity[valid]
    depth[(depth < 0.5) | (depth > max_depth_m)] = np.nan
    return depth


def bbox_depth(
    depth: np.ndarray | None,
    bbox: tuple[float, float, float, float],
    *,
    min_pixels: int = 20,
) -> float | None:
    if depth is None:
        return None
    h, w = depth.shape[:2]
    x1, y1, x2, y2 = [round(value) for value in bbox]
    x1, x2 = sorted((max(0, x1), min(w, x2)))
    y1, y2 = sorted((max(0, y1), min(h, y2)))
    if x2 <= x1 or y2 <= y1:
        return None
    crop = depth[y1:y2, x1:x2]
    valid = crop[np.isfinite(crop) & (crop > 0.5)]
    if valid.size < min_pixels:
        return None
    return float(np.median(valid))


def geometry_depth(detection: Detection, calibration: Calibration) -> float | None:
    if detection.dimensions is None:
        return None
    height_m = max(float(detection.dimensions[0]), 0.2)
    bbox_height = max(detection.bbox[3] - detection.bbox[1], 1.0)
    return float(calibration.fy * height_m / bbox_height)


def lateral_from_bbox(
    bbox: tuple[float, float, float, float],
    distance_m: float,
    calibration: Calibration,
) -> float:
    center_x = (bbox[0] + bbox[2]) / 2.0
    return float((center_x - calibration.cx) * distance_m / calibration.fx)


def attach_distances(
    detections: list[Detection],
    depth: np.ndarray | None,
    calibration: Calibration,
    *,
    prefer_label3d: bool = True,
) -> None:
    for detection in detections:
        if (
            prefer_label3d
            and detection.location is not None
            and detection.location[2] > 0.1
        ):
            detection.distance_m = float(detection.location[2])
            detection.lateral_m = float(detection.location[0])
            detection.distance_source = "label3d"
            continue
        distance_m = bbox_depth(depth, detection.bbox)
        if distance_m is not None:
            detection.distance_m = distance_m
            detection.lateral_m = lateral_from_bbox(
                detection.bbox, distance_m, calibration
            )
            detection.distance_source = "depth_roi"
            continue
        distance_m = geometry_depth(detection, calibration)
        if distance_m is not None:
            detection.distance_m = distance_m
            detection.lateral_m = lateral_from_bbox(
                detection.bbox, distance_m, calibration
            )
            detection.distance_source = "single_view_geometry"


def summarize_depth(
    depth: np.ndarray | None,
    source: Literal["ground_truth", "stereo", "geometry", "temporal"],
) -> DepthEstimate:
    if depth is None or depth.size == 0:
        return DepthEstimate(
            source=source,
            median_depth_m=None,
            valid_coverage=0.0,
            confidence=0.0,
        )
    valid = depth[np.isfinite(depth) & (depth >= 0.0)]
    coverage = float(valid.size / depth.size)
    return DepthEstimate(
        source=source,
        median_depth_m=float(np.median(valid)) if valid.size else None,
        valid_coverage=coverage,
        confidence=1.0 if source == "ground_truth" and valid.size else coverage,
    )


def _grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.uint8, copy=False)
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    raise ValueError("Stereo images must be grayscale or three-channel BGR")
