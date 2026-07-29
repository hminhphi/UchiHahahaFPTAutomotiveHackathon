from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fleetiq_contracts import InferenceRequest, InferenceResponse
from fleetiq_contracts.inference import DriverState
from fleetiq_dms.worker import DmsWorker


def request(*, trip_id: str = "T01-Sample", view: str = "driver") -> InferenceRequest:
    return InferenceRequest(
        schema_version="1.0",
        request_id=uuid4(),
        correlation_id="correlation-1",
        trip_id=trip_id,
        frame_index=1,
        producer="dms-worker",
        occurred_at=datetime.now(UTC),
        model_name="dms",
        frame_artifact_uri="data/frame.jpg",
        camera_view=view,
    )


class FakeClient:
    def __init__(self, state: str | None = "attentive") -> None:
        self.state = state

    def infer(self, value: InferenceRequest) -> InferenceResponse:
        driver_state = None
        if self.state is not None:
            driver_state = DriverState(state=self.state, confidence=0.9)
        return InferenceResponse(
            schema_version="1.0",
            request_id=value.request_id,
            correlation_id=value.correlation_id,
            trip_id=value.trip_id,
            frame_index=value.frame_index,
            producer="dms-model",
            occurred_at=value.occurred_at,
            driver_state=driver_state,
        )


def test_worker_smooths_each_trip_independently() -> None:
    client = FakeClient("drowsy")
    worker = DmsWorker(client, window_size=3, min_votes=2)

    first_a = worker.process(request(trip_id="T01-Sample"))
    first_b = worker.process(request(trip_id="T02-Sample"))
    second_a = worker.process(request(trip_id="T01-Sample"))

    assert first_a.driver_state.state == "unknown"
    assert first_a.driver_state.confidence == 0.0
    assert first_b.driver_state.state == "unknown"
    assert second_a.driver_state.state == "drowsy"


def test_worker_requires_driver_camera_view() -> None:
    worker = DmsWorker(FakeClient())

    with pytest.raises(ValueError, match="driver camera"):
        worker.process(request(view="road_left"))


def test_worker_rejects_response_without_driver_state() -> None:
    worker = DmsWorker(FakeClient(None))

    with pytest.raises(ValueError, match="driver_state"):
        worker.process(request())
