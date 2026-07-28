"""Internal road-facing runtime types and strict contract conversion."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

import numpy as np
from fleetiq_contracts import InferenceResponse
from fleetiq_contracts.inference import (
    BoundingBox,
    DepthState,
    LaneState,
)
from fleetiq_contracts.inference import (
    Detection as ContractDetection,
)


@dataclass(slots=True)
class Detection:
    """One road-object observation before or after association."""

    object_type: str
    bbox: tuple[float, float, float, float]
    confidence: float = 1.0
    dimensions: tuple[float, float, float] | None = None
    location: tuple[float, float, float] | None = None
    rotation_y: float | None = None
    source: str = "unknown"
    track_id: int | None = None
    distance_m: float | None = None
    lateral_m: float | None = None
    relative_speed_mps: float | None = None
    ttc_s: float | None = None
    distance_source: str = "none"


@dataclass(frozen=True, slots=True)
class RoadPlane:
    """A camera-space road plane."""

    normal: np.ndarray
    d: float
    inlier_ratio: float
    inlier_count: int
    source: str = "depth_ransac"


@dataclass(slots=True)
class LaneEstimate:
    """Metric lane state with optional evidence masks for rendering/filtering."""

    detected: bool = True
    lane_offset_m: float | None = None
    heading_deg: float | None = None
    confidence: float = 0.0
    road_mask: np.ndarray | None = field(default=None, repr=False)
    lane_mask: np.ndarray | None = field(default=None, repr=False)
    corridor_mask: np.ndarray | None = field(default=None, repr=False)
    vertical_corridor_mask: np.ndarray | None = field(default=None, repr=False)
    line_segments: list[tuple[int, int, int, int]] = field(
        default_factory=list, repr=False
    )
    plane: RoadPlane | None = None
    source: str = "unknown"
    note: str = ""


@dataclass(frozen=True, slots=True)
class DepthEstimate:
    """Frame-level summary of a depth map."""

    source: Literal["ground_truth", "stereo", "geometry", "temporal"]
    median_depth_m: float | None
    valid_coverage: float
    confidence: float
    artifact_uri: str | None = None


@dataclass(frozen=True, slots=True)
class TrackedObstacle:
    """Motion state for one associated object."""

    track_id: int
    timestamp_s: float
    distance_m: float
    relative_speed_mps: float | None = None
    ttc_s: float | None = None


@dataclass(frozen=True, slots=True)
class RoadFrameResult:
    """One complete frame result at the service boundary."""

    request_id: UUID
    correlation_id: str
    trip_id: str
    frame_index: int
    occurred_at: datetime
    detections: tuple[Detection, ...] = ()
    lane: LaneEstimate | None = None
    depth: DepthEstimate | None = None
    producer: str = "roadface-worker"

    def to_inference_response(self) -> InferenceResponse:
        """Convert internal values to the strict, JSON-safe wire contract."""
        contract_detections = tuple(
            ContractDetection(
                track_id=str(detection.track_id or f"untracked-{index}"),
                label=detection.object_type,
                bounding_box=BoundingBox(
                    x_min=float(detection.bbox[0]),
                    y_min=float(detection.bbox[1]),
                    x_max=float(detection.bbox[2]),
                    y_max=float(detection.bbox[3]),
                ),
                confidence=float(np.clip(detection.confidence, 0.0, 1.0)),
                distance_m=_finite_or_none(detection.distance_m),
                relative_speed_mps=_finite_or_none(detection.relative_speed_mps),
                ttc_s=_positive_finite_or_none(detection.ttc_s),
            )
            for index, detection in enumerate(self.detections, start=1)
        )
        lane_state = None
        if self.lane is not None:
            lane_state = LaneState(
                detected=self.lane.detected,
                lane_offset_m=_finite_or_none(self.lane.lane_offset_m),
                heading_error_deg=_finite_or_none(self.lane.heading_deg),
                confidence=float(np.clip(self.lane.confidence, 0.0, 1.0)),
            )
        depth_state = None
        if self.depth is not None:
            depth_state = DepthState(
                source=self.depth.source,
                median_depth_m=_non_negative_finite_or_none(self.depth.median_depth_m),
                valid_coverage=float(np.clip(self.depth.valid_coverage, 0.0, 1.0)),
                confidence=float(np.clip(self.depth.confidence, 0.0, 1.0)),
                artifact_uri=self.depth.artifact_uri,
            )
        return InferenceResponse(
            schema_version="1.0",
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            trip_id=self.trip_id,
            frame_index=self.frame_index,
            producer=self.producer,
            occurred_at=self.occurred_at,
            detections=contract_detections,
            lane_state=lane_state,
            depth_state=depth_state,
            driver_state=None,
        )

    def write_json(self, path: Path) -> Path:
        """Write the strict response as one UTF-8 JSON document."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.to_inference_response().model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path


def _finite_or_none(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return float(value)


def _positive_finite_or_none(value: float | None) -> float | None:
    finite = _finite_or_none(value)
    return finite if finite is not None and finite > 0.0 else None


def _non_negative_finite_or_none(value: float | None) -> float | None:
    finite = _finite_or_none(value)
    return finite if finite is not None and finite >= 0.0 else None
