"""FleetIQ camera WebSocket binary frame protocol."""

import json
from dataclasses import dataclass
from datetime import datetime

from fleetiq_contracts.base import RFC3339DateTime, VersionedModel
from pydantic import Field, ValidationError, field_validator


class CameraFrameMetadata(VersionedModel):
    frame_index: int = Field(ge=0)
    occurred_at: RFC3339DateTime
    width: int = Field(gt=0, le=16384)
    height: int = Field(gt=0, le=16384)
    correlation_id: str = Field(min_length=1, max_length=128)

    @field_validator("occurred_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone offset")
        return value


@dataclass(frozen=True)
class CameraFrame:
    metadata: CameraFrameMetadata
    jpeg: bytes


class FrameProtocolError(ValueError):
    def __init__(self, message: str, close_code: int) -> None:
        super().__init__(message)
        self.close_code = close_code


def decode_camera_frame(
    payload: bytes,
    max_metadata_bytes: int,
    max_frame_bytes: int,
) -> CameraFrame:
    """Decode ``u32be metadata length | JSON metadata | JPEG``."""
    if len(payload) < 4:
        raise FrameProtocolError("missing metadata length", 1007)

    metadata_length = int.from_bytes(payload[:4], "big", signed=False)
    if metadata_length > max_metadata_bytes:
        raise FrameProtocolError("metadata exceeds configured limit", 1009)
    if metadata_length == 0 or len(payload) < 4 + metadata_length:
        raise FrameProtocolError("invalid metadata length", 1007)

    metadata_bytes = payload[4 : 4 + metadata_length]
    jpeg = payload[4 + metadata_length :]
    if len(jpeg) > max_frame_bytes:
        raise FrameProtocolError("frame exceeds configured limit", 1009)

    try:
        raw_metadata = json.loads(metadata_bytes.decode("utf-8"))
        if not isinstance(raw_metadata, dict):
            raise TypeError("metadata must be an object")
        metadata = CameraFrameMetadata.model_validate(raw_metadata)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValidationError) as error:
        raise FrameProtocolError("invalid frame metadata", 1007) from error

    if len(jpeg) < 4 or not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
        raise FrameProtocolError("payload is not a JPEG frame", 1003)
    return CameraFrame(metadata=metadata, jpeg=jpeg)
