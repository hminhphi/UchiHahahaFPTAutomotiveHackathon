import json
from datetime import UTC, datetime
from io import BytesIO
from types import ModuleType
from typing import Any
from unittest.mock import ANY
from uuid import UUID

import pytest
from fleetiq_contracts import InferenceRequest, InferenceResponse
from fleetiq_model_clients.config import (
    EndpointKind,
    SageMakerEndpointSettings,
)
from fleetiq_model_clients.sagemaker import (
    SageMakerInvocationError,
    SageMakerModelClient,
    SageMakerResponseIdentityError,
)

ROAD_RESPONSE = b"""{
  "schema_version": "1.0",
  "request_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "correlation_id": "trip-42-frame-7",
  "trip_id": "T01-Sample",
  "frame_index": 7,
  "producer": "roadface-model",
  "occurred_at": "2026-07-29T00:00:00+00:00",
  "detections": [],
  "lane_state": null,
  "depth_state": null,
  "driver_state": null
}"""

SENSITIVE_VALUES = (
    "Bearer authorization-secret",
    "AKIA_PRIVATE_CREDENTIAL",
    "private-request-body",
    "X-Amz-Signature=private-signature",
)


class RecordingRuntimeClient:
    def __init__(self, body: bytes = ROAD_RESPONSE) -> None:
        self.body = body
        self.calls: list[dict[str, Any]] = []

    def invoke_endpoint(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "Body": BytesIO(self.body),
            "ContentType": "application/json",
            "InvokedProductionVariant": "AllTraffic",
        }


def make_request(correlation_id: str = "trip-42-frame-7") -> InferenceRequest:
    return InferenceRequest(
        schema_version="1.0",
        request_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        correlation_id=correlation_id,
        trip_id="T01-Sample",
        frame_index=7,
        producer="roadface-worker",
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
        model_name="detector",
        frame_artifact_uri="s3://fleetiq-frames/T01-Sample/000007.jpg",
        camera_view="road_left",
    )


def make_response_body(**updates: object) -> bytes:
    payload = json.loads(ROAD_RESPONSE)
    payload.update(updates)
    return json.dumps(payload).encode("utf-8")


def exception_graph(error: BaseException) -> list[BaseException]:
    found: list[BaseException] = []
    pending = [error]
    while pending:
        current = pending.pop()
        if any(current is item for item in found):
            continue
        found.append(current)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    return found


def assert_sanitized_exception_graph(error: BaseException) -> None:
    graph = exception_graph(error)
    assert graph == [error]
    rendered = "\n".join(f"{item!r}\n{item}" for item in graph)
    for secret in SENSITIVE_VALUES:
        assert secret not in rendered


def test_infer_passes_versioned_request_to_sagemaker_exactly() -> None:
    runtime = RecordingRuntimeClient()
    client = SageMakerModelClient("fleetiq-detector-prod", runtime_client=runtime)
    request = make_request()

    response = client.infer(request)

    assert isinstance(response, InferenceResponse)
    assert runtime.calls == [
        {
            "EndpointName": "fleetiq-detector-prod",
            "Body": request.model_dump_json().encode("utf-8"),
            "ContentType": "application/json",
            "Accept": "application/json",
            "CustomAttributes": "correlation-id=trip-42-frame-7",
        }
    ]


@pytest.mark.parametrize(
    ("field", "mismatched_value"),
    [
        ("request_id", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ("correlation_id", "Bearer authorization-secret"),
        ("trip_id", "T02-Sample"),
        ("frame_index", 8),
        ("occurred_at", "2026-07-29T00:00:01+00:00"),
    ],
)
def test_infer_rejects_response_identity_mismatch(
    field: str,
    mismatched_value: object,
) -> None:
    runtime = RecordingRuntimeClient(make_response_body(**{field: mismatched_value}))
    client = SageMakerModelClient("fleetiq-detector-prod", runtime_client=runtime)

    with pytest.raises(SageMakerResponseIdentityError, match=field) as error:
        client.infer(make_request())

    assert_sanitized_exception_graph(error.value)


def test_infer_accepts_response_timestamp_for_same_instant() -> None:
    runtime = RecordingRuntimeClient(
        make_response_body(occurred_at="2026-07-29T07:00:00+07:00")
    )
    client = SageMakerModelClient("fleetiq-detector-prod", runtime_client=runtime)

    response = client.infer(make_request())

    assert response.occurred_at == make_request().occurred_at


def test_infer_bytes_passes_binary_payload_and_headers_exactly() -> None:
    runtime = RecordingRuntimeClient()
    client = SageMakerModelClient("fleetiq-detector-prod", runtime_client=runtime)
    payload = b"\xff\xd8frame\xff\xd9"

    client.infer_bytes(
        payload,
        content_type="image/jpeg",
        custom_attributes="correlation-id=frame-7",
    )

    assert runtime.calls == [
        {
            "EndpointName": "fleetiq-detector-prod",
            "Body": payload,
            "ContentType": "image/jpeg",
            "Accept": "application/json",
            "CustomAttributes": "correlation-id=frame-7",
        }
    ]


@pytest.mark.parametrize(
    ("kind", "variable"),
    [
        (EndpointKind.DETECTOR, "SAGEMAKER_DETECTOR_ENDPOINT"),
        (EndpointKind.DEPTH, "SAGEMAKER_DEPTH_ENDPOINT"),
        (EndpointKind.LANE, "SAGEMAKER_LANE_ENDPOINT"),
        (EndpointKind.DMS, "SAGEMAKER_DMS_ENDPOINT"),
    ],
)
def test_endpoint_settings_require_named_environment_variable(
    kind: EndpointKind,
    variable: str,
) -> None:
    with pytest.raises(ValueError, match=variable):
        SageMakerEndpointSettings.from_environment(kind, environ={})


def test_from_environment_builds_bounded_botocore_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, Any] = {}

    class FakeConfig:
        def __init__(self, **kwargs: Any) -> None:
            recorded["config"] = kwargs

    boto3 = ModuleType("boto3")

    def client(service_name: str, **kwargs: Any) -> RecordingRuntimeClient:
        recorded["service_name"] = service_name
        recorded["client_kwargs"] = kwargs
        return RecordingRuntimeClient()

    boto3.client = client  # type: ignore[attr-defined]
    botocore = ModuleType("botocore")
    botocore_config = ModuleType("botocore.config")
    botocore_config.Config = FakeConfig  # type: ignore[attr-defined]
    monkeypatch.setitem(__import__("sys").modules, "boto3", boto3)
    monkeypatch.setitem(__import__("sys").modules, "botocore", botocore)
    monkeypatch.setitem(__import__("sys").modules, "botocore.config", botocore_config)

    model_client = SageMakerModelClient.from_environment(
        EndpointKind.DETECTOR,
        environ={"SAGEMAKER_DETECTOR_ENDPOINT": "fleetiq-detector-prod"},
    )

    assert model_client.endpoint_name == "fleetiq-detector-prod"
    assert recorded == {
        "service_name": "sagemaker-runtime",
        "client_kwargs": {"config": ANY},
        "config": {
            "connect_timeout": 3,
            "read_timeout": 30,
            "retries": {"mode": "standard", "total_max_attempts": 3},
        },
    }


def test_invocation_error_is_sanitized() -> None:
    class FailingRuntimeClient:
        def invoke_endpoint(self, **_: Any) -> dict[str, Any]:
            raise RuntimeError(
                "Authorization=Bearer authorization-secret "
                "credential=AKIA_PRIVATE_CREDENTIAL "
                "body=b'private-request-body' "
                "https://bucket.s3.amazonaws.com/a?"
                "X-Amz-Signature=private-signature"
            )

    client = SageMakerModelClient(
        "fleetiq-detector-prod",
        runtime_client=FailingRuntimeClient(),
    )

    with pytest.raises(SageMakerInvocationError) as error:
        client.infer(make_request())

    assert "fleetiq-detector-prod" in str(error.value)
    assert_sanitized_exception_graph(error.value)


@pytest.mark.parametrize(
    "private_body",
    [
        pytest.param(
            b'{"authorization":"Bearer authorization-secret",'
            b'"credential":"AKIA_PRIVATE_CREDENTIAL",'
            b'"body":"private-request-body",'
            b'"url":"https://private.example/frame?'
            b'X-Amz-Signature=private-signature"}',
            id="contract-validation",
        ),
        pytest.param(
            b'{"authorization":"Bearer authorization-secret",'
            b'"credential":"AKIA_PRIVATE_CREDENTIAL",'
            b'"body":"private-request-body",'
            b'"url":"https://private.example/frame?'
            b'X-Amz-Signature=private-signature"',
            id="json-parse",
        ),
    ],
)
def test_invalid_response_is_sanitized(private_body: bytes) -> None:
    client = SageMakerModelClient(
        "fleetiq-detector-prod",
        runtime_client=RecordingRuntimeClient(private_body),
    )

    with pytest.raises(SageMakerInvocationError) as error:
        client.infer(make_request())

    assert "invalid InferenceResponse" in str(error.value)
    assert_sanitized_exception_graph(error.value)


def test_stream_read_error_is_sanitized() -> None:
    class FailingBody:
        def read(self) -> bytes:
            raise RuntimeError(
                "Authorization=Bearer authorization-secret "
                "credential=AKIA_PRIVATE_CREDENTIAL "
                "body=b'private-request-body' "
                "https://private.example/frame?"
                "X-Amz-Signature=private-signature"
            )

    class ReadFailingRuntimeClient:
        def invoke_endpoint(self, **_: Any) -> dict[str, Any]:
            return {"Body": FailingBody()}

    client = SageMakerModelClient(
        "fleetiq-detector-prod",
        runtime_client=ReadFailingRuntimeClient(),
    )

    with pytest.raises(SageMakerInvocationError) as error:
        client.infer(make_request())

    assert "invalid InferenceResponse" in str(error.value)
    assert_sanitized_exception_graph(error.value)


def test_custom_attributes_encode_unsafe_correlation_characters() -> None:
    correlation_id = "trip 42?token=private"
    runtime = RecordingRuntimeClient(
        make_response_body(correlation_id=correlation_id)
    )
    client = SageMakerModelClient("fleetiq-detector-prod", runtime_client=runtime)

    client.infer(make_request(correlation_id))

    assert runtime.calls[0]["CustomAttributes"] == (
        "correlation-id=trip%2042%3Ftoken%3Dprivate"
    )
