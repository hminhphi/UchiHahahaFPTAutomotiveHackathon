"""SageMaker inference-toolkit entry points for DMS."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from fleetiq_contracts import InferenceRequest, InferenceResponse
from fleetiq_contracts.inference import DriverState
from pydantic import ValidationError

_MAX_REQUEST_BYTES = 1024 * 1024


class DmsModel(Protocol):
    def predict(self, request: InferenceRequest) -> DriverState | dict[str, Any]: ...


class FixedDmsModel:
    def __init__(self, output: DriverState) -> None:
        self._output = output

    def predict(self, request: InferenceRequest) -> DriverState:
        del request
        return self._output.model_copy(deep=True)


def model_fn(model_dir: str) -> DmsModel:
    config_path = Path(model_dir) / "dms_model.json"
    if not config_path.is_file():
        return FixedDmsModel(DriverState(state="unknown", confidence=0.0))
    try:
        output = DriverState.model_validate_json(config_path.read_bytes())
    except (OSError, ValidationError):
        raise ValueError("invalid DMS model configuration") from None
    return FixedDmsModel(output)


def input_fn(request_body: bytes, content_type: str) -> InferenceRequest:
    if content_type != "application/json":
        raise ValueError("DMS endpoint requires application/json")
    if not request_body or len(request_body) > _MAX_REQUEST_BYTES:
        raise ValueError("DMS request body has an invalid size")
    try:
        request = InferenceRequest.model_validate_json(request_body)
    except ValidationError:
        raise ValueError("invalid DMS inference request") from None
    if request.camera_view != "driver":
        raise ValueError("DMS inference requires the driver camera view")
    return request


def predict_fn(request: InferenceRequest, model: DmsModel) -> InferenceResponse:
    prediction: DriverState | dict[str, Any] | None = None
    failed = False
    try:
        prediction = model.predict(request)
        state = (
            prediction
            if isinstance(prediction, DriverState)
            else DriverState.model_validate(prediction)
        )
    except Exception:  # noqa: BLE001 - model boundary is untrusted
        failed = True
    if failed or prediction is None:
        raise ValueError("invalid DMS model output") from None
    return InferenceResponse(
        schema_version="1.0",
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        trip_id=request.trip_id,
        frame_index=request.frame_index,
        producer="dms-model",
        occurred_at=request.occurred_at,
        driver_state=state,
    )


def output_fn(
    prediction: InferenceResponse,
    accept: str,
) -> tuple[str, str]:
    if accept != "application/json":
        raise ValueError("DMS endpoint produces application/json")
    return prediction.model_dump_json(), "application/json"
