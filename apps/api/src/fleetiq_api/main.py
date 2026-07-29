"""FastAPI application factory for the FleetIQ control plane."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fleetiq_observability import redact

from .config import ApiSettings
from .dependencies import (
    AppDependencies,
    create_external_dependencies,
    create_test_dependencies,
)
from .errors import ApiError
from .routes import health, jobs, trips, websocket
from .schemas import ErrorDetail, ErrorEnvelope, utc_now

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_LOGGER = logging.getLogger("fleetiq.api")


def _trace_id(value: str | None) -> str:
    if value is not None and _SAFE_ID.fullmatch(value):
        return value
    return str(uuid4())


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    envelope = ErrorEnvelope(
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        timestamp=utc_now(),
        error=ErrorDetail(code=code, message=message),
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))


def create_app(
    testing: bool | None = None,
    *,
    settings: ApiSettings | None = None,
    dependencies: AppDependencies | None = None,
    max_metadata_bytes: int | None = None,
    max_frame_bytes: int | None = None,
) -> FastAPI:
    """Create an API with explicit configuration and injectable resources."""
    selected = settings or ApiSettings.from_environment(os.environ, testing_override=testing)
    updates: dict[str, int] = {}
    if max_metadata_bytes is not None:
        updates["max_metadata_bytes"] = max_metadata_bytes
    if max_frame_bytes is not None:
        updates["max_frame_bytes"] = max_frame_bytes
    if updates:
        selected = selected.model_copy(update=updates)
        selected = ApiSettings.model_validate(selected.model_dump())

    if dependencies is None:
        if selected.testing:
            dependencies = create_test_dependencies()
        else:
            assert selected.redis_url is not None
            assert selected.database_url is not None
            dependencies = create_external_dependencies(selected.redis_url, selected.database_url)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resources = (application.state.dependencies.redis, application.state.dependencies.database)
        started = []
        try:
            for resource in resources:
                await resource.start()
                started.append(resource)
            yield
        finally:
            for resource in reversed(started):
                await resource.close()

    application = FastAPI(title="FleetIQ API", version="1.0.0", lifespan=lifespan)
    application.state.settings = selected
    application.state.dependencies = dependencies
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(selected.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Correlation-ID",
            "X-Request-ID",
        ],
    )

    @application.middleware("http")
    async def trace_request(request: Request, call_next):
        started_at = perf_counter()
        request_id = _trace_id(request.headers.get("X-Request-ID"))
        correlation_id = _trace_id(request.headers.get("X-Correlation-ID") or request_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        _LOGGER.info(
            "request_complete",
            extra={
                "fleetiq": redact(
                    {
                        "request_id": request_id,
                        "correlation_id": correlation_id,
                        "method": request.method,
                        "url": str(request.url),
                        "status_code": response.status_code,
                        "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                        "headers": {
                            "authorization": request.headers.get("Authorization"),
                            "idempotency-key": request.headers.get("Idempotency-Key"),
                        },
                    }
                )
            },
        )
        return response

    @application.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return _error_response(request, error.status_code, error.code, error.message)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return _error_response(request, 422, "validation_error", "Request payload is invalid")

    application.include_router(health.router)
    application.include_router(trips.router)
    application.include_router(jobs.router)
    application.include_router(websocket.router)
    return application


# Offline app for OpenAPI inspection. Production containers use ``create_app`` as a factory.
app = create_app(testing=True)
