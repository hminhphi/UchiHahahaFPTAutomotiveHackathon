"""Strict records for FleetIQ's operational trip store."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fleetiq_contracts.base import ContractModel, validate_artifact_reference, validate_mqtt_segment
from pydantic import AfterValidator, Field, field_validator


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return value.astimezone(UTC)


SafeIdentifier = Annotated[str, AfterValidator(validate_mqtt_segment)]
UTCDateTime = Annotated[datetime, AfterValidator(_aware_datetime)]
MediaView = Literal["road_left", "road_right", "driver", "depth"]


class VehicleRecord(ContractModel):
    vehicle_id: SafeIdentifier
    vehicle_class: str = Field(min_length=1, max_length=64)
    license_plate: str = Field(min_length=1, max_length=32)
    length_m: float = Field(gt=0, le=30)
    width_m: float = Field(gt=0, le=5)
    height_m: float = Field(gt=0, le=6)
    payload_capacity_kg: float = Field(ge=0, le=100_000)
    depot_name: str | None = Field(default=None, min_length=1, max_length=120)


class DriverRecord(ContractModel):
    driver_id: SafeIdentifier
    display_name: str = Field(min_length=1, max_length=120)
    employee_code: SafeIdentifier | None = None
    license_class: str | None = Field(default=None, min_length=1, max_length=32)
    home_depot: str | None = Field(default=None, min_length=1, max_length=120)


class DeliveryOrderRecord(ContractModel):
    order_id: SafeIdentifier
    trip_id: SafeIdentifier
    status: Literal["planned", "loaded", "in_transit", "delivered", "exception"]
    cargo_class: str = Field(min_length=1, max_length=64)
    package_count: int = Field(ge=0, le=100_000)
    weight_kg: float | None = Field(default=None, ge=0, le=100_000)
    destination: str | None = Field(default=None, min_length=1, max_length=160)


class TripDetail(ContractModel):
    trip_id: SafeIdentifier
    vehicle_id: SafeIdentifier
    driver_id: SafeIdentifier
    source: Literal["historical", "live"]
    status: Literal["planned", "active", "complete", "failed"]
    order_count: int = Field(ge=0, le=100_000)
    cargo_class: str = Field(min_length=1, max_length=64)
    vehicle_class: str = Field(min_length=1, max_length=64)
    organizer_trip_id: SafeIdentifier | None = None
    seed_version: str | None = Field(default=None, min_length=1, max_length=64)
    route_name: str | None = Field(default=None, min_length=1, max_length=160)
    started_at: UTCDateTime | None = None
    ended_at: UTCDateTime | None = None


class VideoFrameMapEntry(ContractModel):
    frame_index: int = Field(ge=0)
    time_s: float = Field(ge=0)


class RoadVideoDescriptor(ContractModel):
    trip_id: SafeIdentifier
    asset_url: str = Field(min_length=1, max_length=2048)
    fps: float = Field(gt=0, le=60)
    duration_s: float = Field(ge=0)
    frame_map: tuple[VideoFrameMapEntry, ...] = ()

    @field_validator("asset_url")
    @classmethod
    def validate_asset_url(cls, value: str) -> str:
        if value.startswith("/api/"):
            return value
        return validate_artifact_reference(value)

    @field_validator("frame_map")
    @classmethod
    def validate_frame_map(cls, value: tuple[VideoFrameMapEntry, ...]) -> tuple[VideoFrameMapEntry, ...]:
        if any(right.time_s <= left.time_s for left, right in zip(value, value[1:], strict=False)):
            raise ValueError("frame map times must be strictly increasing")
        return value


class EventMarker(ContractModel):
    event_id: SafeIdentifier
    trip_id: SafeIdentifier
    frame_index: int = Field(ge=0)
    severity: int = Field(ge=1, le=5)
    event_type: SafeIdentifier
    title: str = Field(min_length=1, max_length=160)
    confidence: float = Field(ge=0, le=1)


class LiveTelemetryInput(ContractModel):
    frame_index: int = Field(ge=0)
    timestamp_s: float = Field(ge=0)
    speed_kmh: float = Field(ge=0, le=300)
    longitudinal_accel_mps2: float | None = Field(default=None, ge=-250, le=250)
    lateral_accel_mps2: float | None = Field(default=None, ge=-250, le=250)
    observed_at: UTCDateTime = Field(default_factory=lambda: datetime.now(UTC))


class LiveSessionInput(ContractModel):
    vehicle_id: SafeIdentifier
    driver_id: SafeIdentifier
    driver_name: str = Field(min_length=1, max_length=120)
    vehicle_class: str = Field(default="connected_delivery_van", min_length=1, max_length=64)
    license_plate: str = Field(min_length=1, max_length=32)
    route_name: str = Field(default="Live logistics route", min_length=1, max_length=160)


class LiveMediaInput(ContractModel):
    view: MediaView
    sequence: int = Field(ge=0)
    content_type: Literal["image/jpeg", "video/mp4"]
    frame_index: int | None = Field(default=None, ge=0)
    timestamp_s: float | None = Field(default=None, ge=0)
    content_length: int | None = Field(default=None, ge=1, le=25 * 1024 * 1024)
