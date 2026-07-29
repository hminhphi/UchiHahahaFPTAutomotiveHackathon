"""Typed HTTP envelope models owned by the API boundary."""

from datetime import UTC, datetime
from typing import Literal

from fleetiq_contracts.base import ContractModel
from pydantic import Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApiEnvelope(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    timestamp: datetime


class HealthData(ContractModel):
    dependencies: dict[str, bool] = Field(default_factory=dict)


class HealthEnvelope(ApiEnvelope):
    status: Literal["ok", "degraded"]
    data: HealthData


class TripSummary(ContractModel):
    trip_id: str
    status: Literal["available", "processing", "complete", "failed"] = "available"


class TripListData(ContractModel):
    items: tuple[TripSummary, ...] = ()


class TripListEnvelope(ApiEnvelope):
    status: Literal["ok"] = "ok"
    data: TripListData


class AnalysisJobCreate(ContractModel):
    trip_id: str = Field(min_length=1, max_length=128)


class AnalysisJob(ContractModel):
    job_id: str
    trip_id: str
    status: Literal["queued", "running", "complete", "failed"]
    idempotency_key: str
    created_at: datetime


class JobEnvelope(ApiEnvelope):
    status: Literal["accepted", "ok"]
    data: AnalysisJob


class ErrorDetail(ContractModel):
    code: str
    message: str


class ErrorEnvelope(ApiEnvelope):
    status: Literal["error"] = "error"
    error: ErrorDetail
