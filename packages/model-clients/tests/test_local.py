import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fleetiq_contracts import InferenceRequest, InferenceResponse
from fleetiq_model_clients.base import ModelClient
from fleetiq_model_clients.local import LocalFixtureModelClient

FIXTURES = Path(__file__).parent / "fixtures"


def make_request() -> InferenceRequest:
    return InferenceRequest(
        schema_version="1.0",
        request_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        correlation_id="trip-42-frame-7",
        trip_id="T01-Sample",
        frame_index=7,
        producer="roadface-worker",
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
        model_name="detector",
        frame_artifact_uri="s3://fleetiq-frames/T01-Sample/000007.jpg",
        camera_view="road_left",
    )


def test_local_client_returns_deterministic_contract() -> None:
    client = LocalFixtureModelClient.from_fixture(FIXTURES / "road_response.json")

    first = client.infer_bytes(b"same-frame", content_type="image/jpeg")
    second = client.infer_bytes(b"same-frame", content_type="image/jpeg")

    assert first == second
    assert isinstance(first, InferenceResponse)
    assert first.schema_version == "1.0"


def test_local_client_implements_typed_request_interface() -> None:
    client: ModelClient = LocalFixtureModelClient.from_fixture(
        FIXTURES / "road_response.json"
    )
    request = make_request()

    response = client.infer(request)

    assert response.request_id == request.request_id
    assert response.correlation_id == request.correlation_id
    assert response.trip_id == request.trip_id
    assert response.frame_index == request.frame_index
    assert response.occurred_at == request.occurred_at
    assert response.producer == "roadface-model"


def test_local_client_keeps_typed_identity_deterministic() -> None:
    client = LocalFixtureModelClient.from_fixture(FIXTURES / "road_response.json")
    request = make_request()

    first = client.infer(request)
    second = client.infer(request)

    assert first == second
    assert (
        first.request_id,
        first.correlation_id,
        first.trip_id,
        first.frame_index,
        first.occurred_at,
    ) == (
        request.request_id,
        request.correlation_id,
        request.trip_id,
        request.frame_index,
        request.occurred_at,
    )


def test_local_client_rejects_invalid_fixture_without_leaking_contents(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "invalid.json"
    secret = "AKIA_TEST_SECRET"
    fixture.write_text(f'{{"credential": "{secret}"}}', encoding="utf-8")

    with pytest.raises(ValueError) as error:
        LocalFixtureModelClient.from_fixture(fixture)

    assert "invalid InferenceResponse fixture" in str(error.value)
    assert secret not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__context__ is None


def test_import_does_not_eagerly_load_aws_sdk() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import fleetiq_model_clients; "
                "assert 'boto3' not in sys.modules; "
                "assert 'botocore' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
