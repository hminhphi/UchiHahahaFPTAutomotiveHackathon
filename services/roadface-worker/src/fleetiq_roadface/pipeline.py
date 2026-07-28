"""Dependency-injected road-facing frame orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol
from uuid import NAMESPACE_URL, uuid5

import cv2
import numpy as np
from fleetiq_data import (
    Calibration,
    DatasetPaths,
    find_frame,
    load_trip_document,
    parse_calibration,
    parse_kitti_labels,
    resolve_trip,
)
from fleetiq_data.trips import TripRecord

from .depth import (
    attach_distances,
    load_ground_truth_depth,
    stereo_depth,
    summarize_depth,
)
from .geometry import bbox_from_projected_object, valid_bbox
from .lane import (
    estimate_classical_lane,
    estimate_plane_lane,
    filter_detections_by_lane_corridor,
)
from .rendering import draw_overlay
from .tracking import ObstacleTracker
from .types import DepthEstimate, Detection, LaneEstimate, RoadFrameResult


class DetectorClient(Protocol):
    """Injected object detector interface."""

    def __call__(self, image_bgr: np.ndarray) -> Sequence[Detection]: ...


class DepthModelClient(Protocol):
    """Injected monocular depth interface."""

    def __call__(self, image_bgr: np.ndarray) -> np.ndarray: ...


@dataclass(frozen=True, slots=True)
class PipelineOptions:
    detector_source: Literal["labels", "labels_custom", "model", "none"] = "labels"
    custom_label_dir_name: str = "label2_custom"
    depth_source: Literal["gt", "stereo", "model", "none"] = "gt"
    depth_policy: Literal["previous", "nearest", "exact"] = "previous"
    lane_method: Literal["classical", "plane"] = "classical"
    lane_filter: bool = True
    lane_margin_m: float = 0.25
    prefer_label3d: bool = True
    visualize: bool = False


class RoadfacePipeline:
    """Run road-facing inference using only caller-supplied paths and clients."""

    def __init__(
        self,
        *,
        dataset_paths: DatasetPaths,
        output_root: Path,
        detector: DetectorClient | None,
        depth_model: DepthModelClient | None,
    ) -> None:
        self.dataset_paths = dataset_paths
        self.output_root = Path(output_root)
        self.detector = detector
        self.depth_model = depth_model
        self._trackers: dict[str, ObstacleTracker] = {}

    def resolve_trip(self, trip_id: str) -> TripRecord:
        return resolve_trip(self.dataset_paths, trip_id)

    def run_trip(
        self,
        trip: TripRecord,
        *,
        start: int = 0,
        end: int | None = None,
        stride: int = 1,
        max_frames: int | None = None,
        fps: float = 20.0,
        options: PipelineOptions | None = None,
    ) -> list[Path]:
        options = options or PipelineOptions()
        document = load_trip_document(trip)
        raw_frames = document.get("frames", [])
        if not isinstance(raw_frames, list):
            raise TypeError(f"Trip '{trip.trip_id}' frames must be a list")
        if not raw_frames:
            return []
        start = max(0, start)
        end = min(len(raw_frames) - 1, len(raw_frames) - 1 if end is None else end)
        if end < start:
            return []
        written: list[Path] = []
        processed = 0
        self._trackers[trip.trip_id] = ObstacleTracker()
        for list_index in range(start, end + 1, max(1, stride)):
            if max_frames is not None and processed >= max_frames:
                break
            frame = raw_frames[list_index]
            if not isinstance(frame, dict):
                continue
            result = self.process_frame(
                trip,
                frame=frame,
                list_index=list_index,
                fps=fps,
                options=options,
            )
            if result is None:
                continue
            trip_output = self.output_root / trip.trip_id
            written.append(
                result.write_json(trip_output / f"{result.frame_index:06d}.json")
            )
            processed += 1
        return written

    def process_frame(
        self,
        trip: TripRecord,
        *,
        frame: dict[str, Any],
        list_index: int,
        fps: float,
        options: PipelineOptions,
    ) -> RoadFrameResult | None:
        frame_index = _frame_index(frame, list_index)
        left_path = find_frame(trip.image_2_dir, frame_index)
        if left_path is None:
            return None
        left = cv2.imread(str(left_path))
        if left is None:
            return None
        calibration_path = find_frame(
            trip.calib_dir,
            frame_index,
            suffixes=(".txt",),
        )
        if calibration_path is None:
            raise FileNotFoundError(
                f"Calibration missing for {trip.trip_id} frame {frame_index}"
            )
        calibration = parse_calibration(calibration_path)
        depth, depth_estimate = self._depth(
            trip, frame_index, left, calibration, options
        )
        lane = self._lane(left, depth, calibration, options)
        detections = self._detections(trip, frame_index, left, calibration, options)
        attach_distances(
            detections,
            depth,
            calibration,
            prefer_label3d=options.prefer_label3d,
        )
        if options.lane_filter and lane.corridor_mask is not None:
            detections = filter_detections_by_lane_corridor(
                detections,
                lane.corridor_mask,
                lane.vertical_corridor_mask,
                lateral_margin_m=options.lane_margin_m,
            )
        timestamp_s = _timestamp_s(frame, list_index, fps)
        tracker = self._trackers.setdefault(trip.trip_id, ObstacleTracker())
        detections = tracker.update(detections, timestamp_s)
        occurred_at = datetime(1970, 1, 1, tzinfo=UTC) + timedelta(
            seconds=max(0.0, timestamp_s)
        )
        result = RoadFrameResult(
            request_id=uuid5(
                NAMESPACE_URL,
                f"fleetiq://roadface/{trip.trip_id}/{frame_index}",
            ),
            correlation_id=f"{trip.trip_id}-frame-{frame_index}",
            trip_id=trip.trip_id,
            frame_index=frame_index,
            occurred_at=occurred_at,
            detections=tuple(detections),
            lane=lane,
            depth=depth_estimate,
        )
        if options.visualize:
            evidence_path = self.output_root / trip.trip_id / f"{frame_index:06d}.png"
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(evidence_path), draw_overlay(left, detections, lane))
        return result

    def _depth(
        self,
        trip: TripRecord,
        frame_index: int,
        left: np.ndarray,
        calibration: Calibration,
        options: PipelineOptions,
    ) -> tuple[np.ndarray | None, DepthEstimate | None]:
        if options.depth_source == "gt":
            depth = load_ground_truth_depth(
                trip, frame_index, policy=options.depth_policy
            )
            return depth, summarize_depth(depth, "ground_truth")
        if options.depth_source == "stereo":
            right_path = find_frame(trip.image_3_dir, frame_index)
            right = cv2.imread(str(right_path)) if right_path is not None else None
            depth = (
                stereo_depth(left, right, calibration) if right is not None else None
            )
            return depth, summarize_depth(depth, "stereo")
        if options.depth_source == "model":
            if self.depth_model is None:
                raise RuntimeError(
                    "depth_source=model requires an injected depth model"
                )
            depth = np.asarray(self.depth_model(left), dtype=np.float32)
            if depth.shape[:2] != left.shape[:2]:
                depth = cv2.resize(
                    depth,
                    (left.shape[1], left.shape[0]),
                    interpolation=cv2.INTER_CUBIC,
                )
            return depth, summarize_depth(depth, "temporal")
        return None, None

    def _lane(
        self,
        image: np.ndarray,
        depth: np.ndarray | None,
        calibration: Calibration,
        options: PipelineOptions,
    ) -> LaneEstimate:
        if options.lane_method == "plane":
            return estimate_plane_lane(image, depth, calibration)
        return estimate_classical_lane(image)

    def _detections(
        self,
        trip: TripRecord,
        frame_index: int,
        image: np.ndarray,
        calibration: Calibration,
        options: PipelineOptions,
    ) -> list[Detection]:
        if options.detector_source == "model":
            if self.detector is None:
                raise RuntimeError(
                    "detector_source=model requires an injected detector"
                )
            return list(self.detector(image))
        if options.detector_source == "none":
            return []
        label_dir = (
            "label_2"
            if options.detector_source == "labels"
            else options.custom_label_dir_name
        )
        label_path = find_frame(
            trip.label_dir(label_dir),
            frame_index,
            suffixes=(".txt",),
        )
        if label_path is None:
            return []
        source = (
            "kitti_label"
            if options.detector_source == "labels"
            else "locateanything_label"
        )
        return detections_from_labels(
            label_path, calibration, image.shape, source=source
        )


def detections_from_labels(
    label_path: Path,
    calibration: Calibration,
    image_shape: tuple[int, ...],
    *,
    source: str,
) -> list[Detection]:
    height, width = image_shape[:2]
    projection = calibration.projection("P2")
    detections: list[Detection] = []
    for obj in parse_kitti_labels(label_path):
        if obj.object_type in {"DontCare", "Misc"}:
            continue
        bbox = bbox_from_projected_object(obj, projection, width, height)
        if bbox is None:
            bbox = valid_bbox(obj.bbox, width, height)
        if bbox is None:
            continue
        detections.append(
            Detection(
                object_type=obj.object_type,
                bbox=bbox,
                confidence=float(obj.score if obj.score is not None else 1.0),
                dimensions=obj.dimensions,
                location=obj.location if obj.location[2] > 0.1 else None,
                rotation_y=obj.rotation_y,
                source=source,
            )
        )
    return detections


def _frame_index(frame: dict[str, Any], fallback: int) -> int:
    value = frame.get("frame_id", fallback)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return fallback


def _timestamp_s(frame: dict[str, Any], list_index: int, fps: float) -> float:
    value = frame.get("timestamp")
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        timestamp = list_index / max(fps, 1e-6)
    return timestamp if np.isfinite(timestamp) else list_index / max(fps, 1e-6)
