"""Idempotent analysis job routes."""

from fastapi import APIRouter, Header, Request

from ..dependencies import AppDependencies, IdempotencyConflictError
from ..errors import ApiError
from ..schemas import AnalysisJobCreate, JobEnvelope, utc_now

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _validate_idempotency_key(value: str | None) -> str:
    if value is None or not value.strip():
        raise ApiError(400, "missing_idempotency_key", "Idempotency-Key is required")
    if value != value.strip() or len(value) > 128:
        raise ApiError(400, "invalid_idempotency_key", "Idempotency-Key must be 1-128 unpadded characters")
    return value


@router.post("", response_model=JobEnvelope, status_code=202)
async def create_job(
    command: AnalysisJobCreate,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobEnvelope:
    key = _validate_idempotency_key(idempotency_key)
    dependencies: AppDependencies = request.app.state.dependencies
    try:
        job = await dependencies.jobs.create(command, idempotency_key=key)
    except IdempotencyConflictError as error:
        raise ApiError(
            409,
            "idempotency_conflict",
            "Idempotency-Key was already used for a different mutation",
        ) from error
    return JobEnvelope(
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        timestamp=utc_now(),
        status="accepted",
        data=job,
    )


@router.get("/{job_id}", response_model=JobEnvelope)
async def get_job(job_id: str, request: Request) -> JobEnvelope:
    dependencies: AppDependencies = request.app.state.dependencies
    job = await dependencies.jobs.get(job_id)
    if job is None:
        raise ApiError(404, "job_not_found", "Analysis job was not found")
    return JobEnvelope(
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        timestamp=utc_now(),
        status="ok",
        data=job,
    )
