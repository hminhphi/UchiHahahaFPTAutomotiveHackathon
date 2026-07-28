"""Versioned telemetry, risk, and coaching payload contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from .base import (
    ArtifactReference,
    ContractModel,
    EventEnvelope,
    VersionedModel,
    validate_mqtt_segment,
)


class EvidenceReference(ContractModel):
    """An external artifact reference; MQTT never carries camera bytes."""

    artifact_uri: ArtifactReference
    frame_index: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, min_length=1)


class TelemetryEvent(EventEnvelope):
    """A normalized vehicle telemetry observation or detected driving behavior."""

    event_type: Literal[
        "vehicle_state",
        "speeding",
        "harsh_brake",
        "harsh_steering",
        "lane_departure",
    ]
    speed_mps: float | None = Field(default=None, ge=0)
    longitudinal_accel_mps2: float | None = None
    lateral_accel_mps2: float | None = None
    yaw_rate_radps: float | None = None
    speed_limit_mps: float | None = Field(default=None, gt=0)


class RiskEvent(EventEnvelope):
    """An explainable collision or driving-risk assessment."""

    event_id: UUID
    event_type: str = Field(min_length=1)
    severity: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1)
    evidence: tuple[EvidenceReference, ...] = ()

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        return validate_mqtt_segment(value)


class CoachingCommand(VersionedModel):
    """A finite, deduplicated instruction for an in-vehicle coaching channel."""

    command_id: UUID
    event_id: UUID
    correlation_id: str
    vehicle_id: str
    created_at: datetime
    expires_at: datetime
    channel: Literal["visual", "voice", "post_trip"]
    priority: int = Field(ge=1, le=5)
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    dedupe_key: str = Field(min_length=1)

    @field_validator("vehicle_id", "dedupe_key")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return validate_mqtt_segment(value)

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, value: str) -> str:
        if not value or value.strip() != value:
            raise ValueError("correlation_id must be non-empty and unpadded")
        return value

    @field_validator("created_at", "expires_at")
    @classmethod
    def validate_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone offset")
        return value


class CoachingAck(VersionedModel):
    """An acknowledgement emitted by the target vehicle after command handling."""

    ack_id: UUID
    command_id: UUID
    correlation_id: str
    vehicle_id: str
    acknowledged_at: datetime
    status: Literal["accepted", "displayed", "dismissed", "expired", "failed"]
    detail: str | None = Field(default=None, min_length=1)

    @field_validator("vehicle_id")
    @classmethod
    def validate_vehicle_id(cls, value: str) -> str:
        return validate_mqtt_segment(value)

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, value: str) -> str:
        if not value or value.strip() != value:
            raise ValueError("correlation_id must be non-empty and unpadded")
        return value

    @field_validator("acknowledged_at")
    @classmethod
    def validate_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone offset")
        return value
