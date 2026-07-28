"""Shared validation primitives for FleetIQ's versioned payloads."""

from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StringConstraints,
    field_validator,
)

_FORBIDDEN_MQTT_SEGMENT_CHARACTERS = frozenset("/+#")
_ALLOWED_ARTIFACT_SCHEMES = frozenset(("file", "https", "s3"))
_ALLOWED_LOCAL_ARTIFACT_PREFIXES = ("artifacts/", "data/")
_ARTIFACT_REFERENCE_PATTERN = r"^(?:s3://|https://|file://|artifacts/|data/).+$"


def validate_mqtt_segment(value: str) -> str:
    """Return a usable MQTT path segment or raise a clear validation error."""
    if not value or value.strip() != value:
        raise ValueError("MQTT identifier segments must be non-empty and unpadded")
    if any(character in value for character in _FORBIDDEN_MQTT_SEGMENT_CHARACTERS):
        raise ValueError("MQTT identifier segments cannot contain '/', '+', or '#'")
    return value


def validate_artifact_reference(value: str) -> str:
    """Reject inline media and require a bounded external or local artifact reference."""
    if value.strip() != value:
        raise ValueError("artifact references must be unpadded")

    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme not in _ALLOWED_ARTIFACT_SCHEMES:
            raise ValueError("artifact references require an approved external or local scheme")
        if parsed.scheme == "file" and not parsed.path:
            raise ValueError("file artifact references require a path")
        if parsed.scheme in {"https", "s3"} and not parsed.netloc:
            raise ValueError("external artifact references require an authority")
        return value

    if value.startswith(_ALLOWED_LOCAL_ARTIFACT_PREFIXES):
        return value

    raise ValueError("artifact references must use s3://, https://, file://, artifacts/, or data/")


def parse_json_uuid(value: object) -> object:
    """Accept UUID strings emitted by JSON serializers without relaxing scalar strictness."""
    if isinstance(value, str):
        return UUID(value)
    return value


def parse_json_datetime(value: object) -> object:
    """Accept RFC3339 timestamp strings emitted by JSON serializers."""
    if isinstance(value, str):
        if "T" not in value:
            raise ValueError("timestamps must use RFC3339 date-time form")
        return datetime.fromisoformat(value)
    return value


ArtifactReference = Annotated[
    str,
    StringConstraints(min_length=1, max_length=2048, pattern=_ARTIFACT_REFERENCE_PATTERN),
    AfterValidator(validate_artifact_reference),
]
JsonUUID = Annotated[UUID, BeforeValidator(parse_json_uuid)]
RFC3339DateTime = Annotated[datetime, BeforeValidator(parse_json_datetime)]


class ContractModel(BaseModel):
    """Base model that prevents unversioned fields from crossing boundaries."""

    model_config = ConfigDict(extra="forbid", strict=True)


class VersionedModel(ContractModel):
    """A strict payload using the first FleetIQ wire-contract version."""

    schema_version: Literal["1.0"]


class EventEnvelope(VersionedModel):
    """Trace fields shared by telemetry and risk events."""

    event_id: str
    correlation_id: str
    trip_id: str
    frame_index: int
    producer: str
    occurred_at: RFC3339DateTime

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
