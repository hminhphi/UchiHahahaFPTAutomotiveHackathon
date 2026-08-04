from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fleetiq_contracts import InferenceResponse, TelemetryEvent
from fleetiq_contracts.inference import (
    BoundingBox,
    Detection,
    DriverState,
    LaneState,
)
from fleetiq_fusion.worker import FusionWorker


def inference(
    *,
    trip_id: str,
    frame: int,
    road: bool,
    driver_state: str = "distracted",
    phone_use: bool | None = None,
) -> InferenceResponse:
    values = {
        "schema_version": "1.0",
        "request_id": uuid4(),
        "correlation_id": "correlation-1",
        "trip_id": trip_id,
        "frame_index": frame,
        "producer": "roadface-worker" if road else "dms-worker",
        "occurred_at": datetime.now(UTC),
    }
    if road:
        values["detections"] = (
            Detection(
                track_id="lead-1",
                label="car",
                bounding_box=BoundingBox(x_min=1, y_min=1, x_max=2, y_max=2),
                confidence=0.9,
                distance_m=12.0,
                relative_speed_mps=8.0,
                ttc_s=1.4,
            ),
        )
        values["lane_state"] = LaneState(
            detected=True,
            lane_offset_m=0.2,
            heading_error_deg=0.0,
            confidence=0.9,
        )
    else:
        values["driver_state"] = DriverState(
            state=driver_state,
            confidence=0.9,
            phone_use=phone_use,
        )
    return InferenceResponse(**values)


def telemetry(*, trip_id: str, frame: int) -> TelemetryEvent:
    return TelemetryEvent(
        schema_version="1.0",
        event_id="telemetry-1",
        correlation_id="correlation-1",
        trip_id=trip_id,
        frame_index=frame,
        producer="telemetry-worker",
        occurred_at=datetime.now(UTC),
        event_type="vehicle_state",
        speed_mps=18.0,
    )


def test_worker_emits_compound_risk_event() -> None:
    event = FusionWorker().fuse(
        inference(trip_id="T01-Sample", frame=10, road=True),
        inference(trip_id="T01-Sample", frame=10, road=False),
        telemetry(trip_id="T01-Sample", frame=10),
    )

    assert event.severity == 5
    assert event.event_type == "compound_risk"
    assert "short_ttc" in event.explanation


def test_worker_emits_phone_use_compound_risk_event() -> None:
    event = FusionWorker().fuse(
        inference(trip_id="T01-Sample", frame=10, road=True),
        inference(
            trip_id="T01-Sample",
            frame=10,
            road=False,
            driver_state="attentive",
            phone_use=True,
        ),
        telemetry(trip_id="T01-Sample", frame=10),
    )

    assert event.event_type == "compound_risk"
    assert "phone_use" in event.explanation
    assert "compound_risk" in event.explanation


def test_worker_rejects_misaligned_trip() -> None:
    with pytest.raises(ValueError, match="trip"):
        FusionWorker().fuse(
            inference(trip_id="T01-Sample", frame=10, road=True),
            inference(trip_id="T02-Sample", frame=10, road=False),
            telemetry(trip_id="T01-Sample", frame=10),
        )


def test_worker_rejects_misaligned_correlation() -> None:
    dms = inference(trip_id="T01-Sample", frame=10, road=False)
    dms = dms.model_copy(update={"correlation_id": "correlation-2"})

    with pytest.raises(ValueError, match="correlation"):
        FusionWorker().fuse(
            inference(trip_id="T01-Sample", frame=10, road=True),
            dms,
            telemetry(trip_id="T01-Sample", frame=10),
        )
