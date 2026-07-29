"""Liveness and dependency-aware readiness routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..dependencies import AppDependencies
from ..schemas import HealthData, HealthEnvelope, utc_now

router = APIRouter(tags=["health"])


def _trace(request: Request) -> tuple[str, str]:
    return request.state.request_id, request.state.correlation_id


@router.get("/health/live", response_model=HealthEnvelope)
async def live(request: Request) -> HealthEnvelope:
    request_id, correlation_id = _trace(request)
    return HealthEnvelope(
        request_id=request_id,
        correlation_id=correlation_id,
        timestamp=utc_now(),
        status="ok",
        data=HealthData(),
    )


@router.get("/health/ready", response_model=HealthEnvelope)
async def ready(request: Request) -> HealthEnvelope | JSONResponse:
    dependencies: AppDependencies = request.app.state.dependencies
    readiness = {
        "redis": await dependencies.redis.ready(),
        "database": await dependencies.database.ready(),
    }
    request_id, correlation_id = _trace(request)
    envelope = HealthEnvelope(
        request_id=request_id,
        correlation_id=correlation_id,
        timestamp=utc_now(),
        status="ok" if all(readiness.values()) else "degraded",
        data=HealthData(dependencies=readiness),
    )
    if envelope.status == "degraded":
        return JSONResponse(status_code=503, content=envelope.model_dump(mode="json"))
    return envelope
