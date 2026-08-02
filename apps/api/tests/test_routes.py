from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from fleetiq_api.dependencies import create_test_dependencies
from fleetiq_api.main import create_app
from fleetiq_api.schemas import AnalysisJob
from fleetiq_api.ws.frame_protocol import CameraFrame, CameraFrameMetadata


def test_trip_list_uses_stable_typed_envelope() -> None:
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/v1/trips")

    assert response.status_code == 200
    assert response.json()["schema_version"] == "1.0"
    assert response.json()["data"] == {"items": []}
    assert response.json()["request_id"]


def test_job_creation_requires_idempotency_key() -> None:
    with TestClient(create_app(testing=True)) as client:
        response = client.post("/api/v1/jobs", json={"trip_id": "T01-Sample"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_idempotency_key"


def test_repeated_job_creation_returns_same_job() -> None:
    headers = {"Idempotency-Key": "analyze-T01"}
    with TestClient(create_app(testing=True)) as client:
        first = client.post("/api/v1/jobs", json={"trip_id": "T01-Sample"}, headers=headers)
        second = client.post("/api/v1/jobs", json={"trip_id": "T01-Sample"}, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["job_id"] == second.json()["data"]["job_id"]
    assert first.json()["data"]["status"] == "queued"


def test_reusing_idempotency_key_for_different_trip_is_conflict() -> None:
    headers = {"Idempotency-Key": "one-operation"}
    with TestClient(create_app(testing=True)) as client:
        client.post("/api/v1/jobs", json={"trip_id": "T01-Sample"}, headers=headers)
        response = client.post("/api/v1/jobs", json={"trip_id": "T02-Sample"}, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"


@pytest.mark.parametrize("trip_id", [" T01", "T01 ", "T 01", "T01\tSample", "T01\nSample", "T01\u0000"])
def test_job_creation_rejects_unsafe_trip_identifier(trip_id: str) -> None:
    with TestClient(create_app(testing=True)) as client:
        response = client.post(
            "/api/v1/jobs",
            json={"trip_id": trip_id},
            headers={"Idempotency-Key": "invalid-trip"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_job_route_rejects_naive_timestamp_from_repository() -> None:
    class BadJobRepository:
        async def create(self, command, *, idempotency_key):
            return AnalysisJob.model_construct(
                job_id="job-bad-time",
                trip_id=command.trip_id,
                status="queued",
                idempotency_key=idempotency_key,
                created_at=datetime(2026, 7, 29, 12, 0),  # noqa: DTZ001 - invalid fixture
            )

        async def get(self, job_id):
            return None

    dependencies = create_test_dependencies()
    dependencies.jobs = BadJobRepository()

    with TestClient(create_app(testing=True, dependencies=dependencies)) as client:
        response = client.post(
            "/api/v1/jobs",
            json={"trip_id": "T01-Sample"},
            headers={"Idempotency-Key": "bad-repository-time"},
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "invalid_repository_data"


def test_historical_frame_route_serves_an_exact_jpeg() -> None:
    class FrameReader:
        async def get_frame(self, trip_id, view, frame_index):
            assert (trip_id, view, frame_index) == ("T01-Sample", "road_left", 42)
            return CameraFrame(
                metadata=CameraFrameMetadata(
                    schema_version="1.0",
                    frame_index=42,
                    occurred_at=datetime.now().astimezone(),
                    width=640,
                    height=360,
                    correlation_id="test.frame.000042",
                ),
                jpeg=b"test-jpeg",
            )

    dependencies = create_test_dependencies()
    dependencies.frame_reader = FrameReader()
    with TestClient(create_app(testing=True, dependencies=dependencies)) as client:
        response = client.get("/api/v1/trips/T01-Sample/frames/road_left/42")

    assert response.status_code == 200
    assert response.content == b"test-jpeg"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-fleetiq-frame-index"] == "42"
