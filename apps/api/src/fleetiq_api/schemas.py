"""Typed HTTP envelope models owned by the API boundary."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fleetiq_contracts.base import ContractModel, validate_mqtt_segment
from pydantic import AfterValidator, Field, field_validator


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return value.astimezone(UTC)


UTCDateTime = Annotated[datetime, AfterValidator(_utc_datetime)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApiEnvelope(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    timestamp: UTCDateTime


class HealthData(ContractModel):
    dependencies: dict[str, bool] = Field(default_factory=dict)


class HealthEnvelope(ApiEnvelope):
    status: Literal["ok", "degraded"]
    data: HealthData


class TripSummary(ContractModel):
    trip_id: str
    status: Literal["available", "processing", "complete", "failed"] = "available"
    safety_score: int | None = Field(default=None, ge=0, le=100)
    severity: int | None = Field(default=None, ge=1, le=5)
    latest_alert: str | None = Field(default=None, max_length=160)
    driver_state: str | None = Field(default=None, max_length=64)
    max_speed_kmh: float | None = Field(default=None, ge=0, le=300)

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, value: str) -> str:
        return validate_mqtt_segment(value)


class TripListData(ContractModel):
    items: tuple[TripSummary, ...] = ()


class TripListEnvelope(ApiEnvelope):
    status: Literal["ok"] = "ok"
    data: TripListData


class TrajectoryPoint(ContractModel):
    frame_index: int = Field(ge=0)
    timestamp_s: float = Field(ge=0)
    x_m: float
    y_m: float
    speed_kmh: float = Field(ge=0, le=300)
    longitudinal_accel_mps2: float = Field(ge=-12, le=12)
    lateral_accel_mps2: float = Field(ge=-12, le=12)
    min_ttc_s: float | None = Field(default=None, ge=0)
    headway_s: float | None = Field(default=None, ge=0)
    driver_state: str = Field(default="unknown", max_length=64)
    driver_alertness: float | None = Field(default=None, ge=0, le=1)
    simulator_risk_score: float | None = Field(default=None, ge=0, le=100)
    active_event_types: tuple[str, ...] = ()
    events: tuple[str, ...] = ()


class TrajectoryData(ContractModel):
    trip_id: str
    points: tuple[TrajectoryPoint, ...] = ()
    distance_m: float = Field(ge=0)
    max_speed_kmh: float = Field(ge=0)
    max_lateral_accel_mps2: float = Field(ge=0)


class TrajectoryEnvelope(ApiEnvelope):
    data: TrajectoryData


class AnalysisJobCreate(ContractModel):
    trip_id: str = Field(min_length=1, max_length=128)

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, value: str) -> str:
        return validate_mqtt_segment(value)


class AnalysisJob(ContractModel):
    job_id: str
    trip_id: str
    status: Literal["queued", "running", "complete", "failed"]
    idempotency_key: str
    created_at: UTCDateTime

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, value: str) -> str:
        return validate_mqtt_segment(value)


class JobEnvelope(ApiEnvelope):
    status: Literal["accepted", "ok"]
    data: AnalysisJob


class ErrorDetail(ContractModel):
    code: str
    message: str


class ErrorEnvelope(ApiEnvelope):
    status: Literal["error"] = "error"
    error: ErrorDetail
