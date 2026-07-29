from fastapi.testclient import TestClient
from fleetiq_api.main import create_app


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
