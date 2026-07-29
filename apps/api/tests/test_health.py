import json
import logging
from datetime import datetime

from fastapi.testclient import TestClient
from fleetiq_api.dependencies import AppDependencies, create_test_dependencies
from fleetiq_api.main import create_app


def test_health_envelope_has_trace_ids_and_utc_timestamp() -> None:
    with TestClient(create_app(testing=True)) as client:
        response = client.get(
            "/health/live",
            headers={"X-Request-ID": "request-123", "X-Correlation-ID": "correlation-123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["status"] == "ok"
    assert body["request_id"] == "request-123"
    assert body["correlation_id"] == "correlation-123"
    assert datetime.fromisoformat(body["timestamp"]).utcoffset() is not None
    assert response.headers["X-Request-ID"] == "request-123"
    assert response.headers["X-Correlation-ID"] == "correlation-123"


def test_ready_reports_unavailable_dependency_without_failing_liveness() -> None:
    dependencies = create_test_dependencies()
    dependencies.redis.set_ready(False)
    app = create_app(testing=True, dependencies=dependencies)

    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["data"]["dependencies"]["redis"] is False


def test_lifespan_starts_and_closes_injected_dependencies() -> None:
    dependencies: AppDependencies = create_test_dependencies()

    with TestClient(create_app(testing=True, dependencies=dependencies)):
        assert dependencies.redis.started is True
        assert dependencies.database.started is True

    assert dependencies.redis.closed is True
    assert dependencies.database.closed is True


def test_request_log_contains_ids_and_redacts_authorization(caplog) -> None:
    caplog.set_level(logging.INFO, logger="fleetiq.api")

    with TestClient(create_app(testing=True)) as client:
        client.get(
            "/health/live",
            headers={
                "Authorization": "Bearer should-not-leak",
                "X-Request-ID": "request-log",
                "X-Correlation-ID": "correlation-log",
            },
        )

    records = [
        record for record in caplog.records if getattr(record, "fleetiq", {}).get("request_id") == "request-log"
    ]
    assert records
    serialized = json.dumps(records[-1].fleetiq)
    assert "should-not-leak" not in serialized
    assert records[-1].fleetiq["correlation_id"] == "correlation-log"


def test_cors_allows_only_configured_origin() -> None:
    app = create_app(testing=True)
    with TestClient(app) as client:
        allowed = client.options(
            "/api/v1/trips",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.options(
            "/api/v1/trips",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers
