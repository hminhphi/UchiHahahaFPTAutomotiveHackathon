"""Typed model request and response contracts for CPU-safe service boundaries."""

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .base import (
    ArtifactReference,
    ContractModel,
    JsonUUID,
    RFC3339DateTime,
    VersionedModel,
    validate_mqtt_segment,
)


class BoundingBox(ContractModel):
    """Image-space detection coordinates in pixels."""

    x_min: float = Field(ge=0)
    y_min: float = Field(ge=0)
    x_max: float = Field(ge=0)
    y_max: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_coordinate_order(self) -> "BoundingBox":
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("bounding boxes require max coordinates above min coordinates")
        return self


class Detection(ContractModel):
    """A typed object detection, with optional spatial risk measurements."""

    track_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    bounding_box: BoundingBox
    confidence: float = Field(ge=0, le=1)
    distance_m: float | None = Field(default=None, ge=0)
    relative_speed_mps: float | None = None
    ttc_s: float | None = Field(default=None, gt=0)


class LaneState(ContractModel):
    """A typed road-lane estimate for one frame."""

    detected: bool
    lane_offset_m: float | None = None
    heading_error_deg: float | None = None
    confidence: float = Field(ge=0, le=1)


class DepthState(ContractModel):
    """A typed depth estimate without embedding depth-map bytes."""

    source: Literal["ground_truth", "stereo", "geometry", "temporal"]
    median_depth_m: float | None = Field(default=None, ge=0)
    valid_coverage: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    artifact_uri: ArtifactReference | None = None


class DriverState(ContractModel):
    """A typed driver-attention estimate for one frame."""

    state: Literal["attentive", "distracted", "drowsy", "unknown"]
    confidence: float = Field(ge=0, le=1)
    eye_closure: float | None = Field(default=None, ge=0, le=1)
    phone_use: bool | None = None
    evidence_uri: ArtifactReference | None = None


class InferenceRequest(VersionedModel):
    """A request that references a frame artifact instead of carrying image bytes."""

    request_id: JsonUUID
    correlation_id: str
    trip_id: str
    frame_index: int = Field(ge=0)
    producer: str
    occurred_at: RFC3339DateTime
    model_name: str
    frame_artifact_uri: ArtifactReference
    camera_view: Literal["road_left", "road_right", "driver"]

    @field_validator("trip_id", "producer", "model_name")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return validate_mqtt_segment(value)

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, value: str) -> str:
        if not value or value.strip() != value:
            raise ValueError("correlation_id must be non-empty and unpadded")
        return value

    @field_validator("occurred_at")
    @classmethod
    def validate_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone offset")
        return value


class InferenceResponse(VersionedModel):
    """A typed inference result with no unstructured model-output dictionaries."""

    request_id: JsonUUID
    correlation_id: str
    trip_id: str
    frame_index: int = Field(ge=0)
    producer: str
    occurred_at: RFC3339DateTime
    detections: tuple[Detection, ...] = Field(default=(), strict=False)
    lane_state: LaneState | None = None
    depth_state: DepthState | None = None
    driver_state: DriverState | None = None

    @field_validator("trip_id", "producer")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return validate_mqtt_segment(value)

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, value: str) -> str:
        if not value or value.strip() != value:
            raise ValueError("correlation_id must be non-empty and unpadded")
        return value

    @field_validator("occurred_at")
    @classmethod
    def validate_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone offset")
        return value
