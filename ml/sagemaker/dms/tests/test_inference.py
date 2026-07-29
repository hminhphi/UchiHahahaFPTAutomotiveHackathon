import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from fleetiq_contracts import InferenceRequest, InferenceResponse


def load_handler() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "inference.py"
    spec = importlib.util.spec_from_file_location("fleetiq_dms_inference", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


handler = load_handler()


def request() -> InferenceRequest:
    return InferenceRequest(
        schema_version="1.0",
        request_id=uuid4(),
        correlation_id="correlation-1",
        trip_id="T01-Sample",
        frame_index=7,
        producer="dms-worker",
        occurred_at=datetime.now(UTC),
        model_name="dms",
        frame_artifact_uri="data/driver/000007.jpg",
        camera_view="driver",
    )


class FakeModel:
    def predict(self, value: InferenceRequest) -> dict[str, object]:
        assert value.camera_view == "driver"
        return {"state": "distracted", "confidence": 0.8, "phone_use": True}


def test_handler_preserves_request_identity() -> None:
    expected = request()

    decoded = handler.input_fn(expected.model_dump_json().encode(), "application/json")
    prediction = handler.predict_fn(decoded, FakeModel())
    body, content_type = handler.output_fn(prediction, "application/json")
    response = InferenceResponse.model_validate_json(body)

    assert content_type == "application/json"
    assert response.request_id == expected.request_id
    assert response.trip_id == expected.trip_id
    assert response.frame_index == expected.frame_index
    assert response.driver_state.state == "distracted"


def test_handler_rejects_unsupported_media_types() -> None:
    with pytest.raises(ValueError, match="application/json"):
        handler.input_fn(b"frame", "image/jpeg")


def test_output_rejects_unsupported_accept_type() -> None:
    with pytest.raises(ValueError, match="application/json"):
        handler.output_fn({"state": "attentive"}, "text/plain")


def test_handler_rejects_invalid_model_output() -> None:
    class BadModel:
        def predict(self, value: InferenceRequest) -> dict[str, object]:
            return {"state": "sleeping", "confidence": 2.0}

    with pytest.raises(ValueError, match="invalid DMS model output"):
        handler.predict_fn(request(), BadModel())
