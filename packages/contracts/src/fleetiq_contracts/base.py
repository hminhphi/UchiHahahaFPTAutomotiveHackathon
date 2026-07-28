"""Shared validation primitives for FleetIQ's versioned payloads."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

SCHEMA_VERSION_V1: Literal["1.0"] = "1.0"
_FORBIDDEN_MQTT_SEGMENT_CHARACTERS = frozenset("/+#")


def validate_mqtt_segment(value: str) -> str:
    """Return a usable MQTT path segment or raise a clear validation error."""
    if not value or value.strip() != value:
        raise ValueError("MQTT identifier segments must be non-empty and unpadded")
    if any(character in value for character in _FORBIDDEN_MQTT_SEGMENT_CHARACTERS):
        raise ValueError("MQTT identifier segments cannot contain '/', '+', or '#'")
    return value


class ContractModel(BaseModel):
    """Base model that prevents unversioned fields from crossing boundaries."""

    model_config = ConfigDict(extra="forbid")


class VersionedModel(ContractModel):
    """A strict payload using the first FleetIQ wire-contract version."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION_V1


class EventEnvelope(VersionedModel):
    """Trace fields shared by telemetry and risk events."""

    event_id: str
    correlation_id: str
    trip_id: str
    frame_index: int
    producer: str
    occurred_at: datetime

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

    @field_validator("frame_index")
    @classmethod
    def validate_frame_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("frame_index must be zero or greater")
        return value

    @field_validator("occurred_at")
    @classmethod
    def validate_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone offset")
        return value
