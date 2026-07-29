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

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, value: str) -> str:
        return validate_mqtt_segment(value)


class TripListData(ContractModel):
    items: tuple[TripSummary, ...] = ()


class TripListEnvelope(ApiEnvelope):
    status: Literal["ok"] = "ok"
    data: TripListData


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
