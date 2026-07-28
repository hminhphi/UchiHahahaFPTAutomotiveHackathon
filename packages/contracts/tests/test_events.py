from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fleetiq_contracts.events import EvidenceReference, RiskEvent
from fleetiq_contracts.inference import (
    BoundingBox,
    DepthState,
    Detection,
    DriverState,
    InferenceRequest,
    InferenceResponse,
    LaneState,
)
from pydantic import ValidationError


def test_risk_event_round_trip_keeps_trace_fields() -> None:
    """Removing trace fields from the event payload would break auditability."""
    event_id = uuid4()
    event = RiskEvent(
        schema_version="1.0",
        event_id=event_id,
        correlation_id="trip-01:frame-100",
        trip_id="T01-Sample",
        frame_index=100,
        producer="fusion-worker",
        occurred_at=datetime(2026, 7, 28, tzinfo=UTC),
        event_type="short_ttc",
        severity=4,
        confidence=0.91,
        explanation="TTC below 1.5 seconds",
    )

    restored = RiskEvent.model_validate_json(event.model_dump_json())

    assert restored.event_id == event_id
    assert restored.frame_index == 100


@pytest.mark.parametrize("field, value", [("severity", 0), ("severity", 6), ("confidence", 1.1)])
def test_risk_event_rejects_out_of_range_safety_values(field: str, value: float) -> None:
    """Relaxing safety ranges would let invalid risk levels cross service boundaries."""
    payload = {
        "schema_version": "1.0",
        "event_id": uuid4(),
        "correlation_id": "trip-01:frame-100",
        "trip_id": "T01-Sample",
        "frame_index": 100,
        "producer": "fusion-worker",
        "occurred_at": datetime(2026, 7, 28, tzinfo=UTC),
        "event_type": "short_ttc",
        "severity": 4,
        "confidence": 0.91,
        "explanation": "TTC below 1.5 seconds",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        RiskEvent.model_validate(payload)


def test_risk_event_rejects_unknown_fields() -> None:
    """Allowing arbitrary fields would silently fork the versioned payload contract."""
    with pytest.raises(ValidationError):
        RiskEvent(
            schema_version="1.0",
            event_id=uuid4(),
            correlation_id="trip-01:frame-100",
            trip_id="T01-Sample",
            frame_index=100,
            producer="fusion-worker",
            occurred_at=datetime(2026, 7, 28, tzinfo=UTC),
            event_type="short_ttc",
            severity=4,
            confidence=0.91,
            explanation="TTC below 1.5 seconds",
            unsupported="nope",
        )


def test_risk_event_requires_a_schema_version() -> None:
    """Omitting the version would make an incoming wire payload ambiguous."""
    with pytest.raises(ValidationError):
        RiskEvent(
            event_id=uuid4(),
            correlation_id="trip-01:frame-100",
            trip_id="T01-Sample",
            frame_index=100,
            producer="fusion-worker",
            occurred_at=datetime(2026, 7, 28, tzinfo=UTC),
            event_type="short_ttc",
            severity=4,
            confidence=0.91,
            explanation="TTC below 1.5 seconds",
        )


@pytest.mark.parametrize(("field", "value"), [("severity", "4"), ("confidence", "0.91")])
def test_risk_event_rejects_coerced_numeric_scalars(field: str, value: str) -> None:
    """Coercing wire scalars would diverge from the exported JSON Schema."""
    payload = {
        "schema_version": "1.0",
        "event_id": uuid4(),
        "correlation_id": "trip-01:frame-100",
        "trip_id": "T01-Sample",
        "frame_index": 100,
        "producer": "fusion-worker",
        "occurred_at": datetime(2026, 7, 28, tzinfo=UTC),
        "event_type": "short_ttc",
        "severity": 4,
        "confidence": 0.91,
        "explanation": "TTC below 1.5 seconds",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        RiskEvent.model_validate(payload)


@pytest.mark.parametrize(
    "artifact_uri",
    ["data:image/jpeg;base64,aGVsbG8=", "base64,aGVsbG8=", "x" * 2049],
)
def test_artifact_references_reject_inline_or_unbounded_content(artifact_uri: str) -> None:
    """Inline content would bypass the camera-byte boundary and MQTT size controls."""
    with pytest.raises(ValidationError):
        EvidenceReference(artifact_uri=artifact_uri)


@pytest.mark.parametrize(
    "factory",
    [
        lambda artifact_uri: EvidenceReference(artifact_uri=artifact_uri),
        lambda artifact_uri: DepthState(
            source="stereo",
            median_depth_m=12.5,
            valid_coverage=0.9,
            confidence=0.87,
            artifact_uri=artifact_uri,
        ),
        lambda artifact_uri: DriverState(
            state="attentive", confidence=0.94, evidence_uri=artifact_uri
        ),
        lambda artifact_uri: InferenceRequest(
            schema_version="1.0",
            request_id=uuid4(),
            correlation_id="T01-Sample:100",
            trip_id="T01-Sample",
            frame_index=100,
            producer="roadface-worker",
            occurred_at=datetime(2026, 7, 28, tzinfo=UTC),
            model_name="roadface-v1",
            frame_artifact_uri=artifact_uri,
            camera_view="road_left",
        ),
    ],
)
def test_all_artifact_fields_reject_inline_data(factory: Callable[[str], object]) -> None:
    """Every artifact-bearing field must preserve the no-inline-media guarantee."""
    with pytest.raises(ValidationError):
        factory("data:image/jpeg;base64,aGVsbG8=")


def test_risk_event_rejects_naive_timestamps() -> None:
    """A naive occurrence time cannot be reliably aligned across producers."""
    with pytest.raises(ValidationError):
        RiskEvent(
            schema_version="1.0",
            event_id=uuid4(),
            correlation_id="trip-01:frame-100",
            trip_id="T01-Sample",
            frame_index=100,
            producer="fusion-worker",
            occurred_at=datetime(2026, 7, 28, tzinfo=UTC).replace(tzinfo=None),
            event_type="short_ttc",
            severity=4,
            confidence=0.91,
            explanation="TTC below 1.5 seconds",
        )


def test_inference_response_uses_typed_vision_and_driver_states() -> None:
    """Replacing typed states with dictionaries would remove validation at the model boundary."""
    response = InferenceResponse(
        schema_version="1.0",
        request_id=uuid4(),
        correlation_id="T01-Sample:100",
        trip_id="T01-Sample",
        frame_index=100,
        producer="roadface-model",
        occurred_at=datetime(2026, 7, 28, tzinfo=UTC),
        detections=(
            Detection(
                track_id="lead-vehicle-1",
                label="car",
                bounding_box=BoundingBox(x_min=10, y_min=20, x_max=110, y_max=120),
                confidence=0.98,
                distance_m=12.5,
            ),
        ),
        lane_state=LaneState(detected=True, lane_offset_m=0.1, confidence=0.88),
        depth_state=DepthState(
            source="stereo",
            median_depth_m=12.5,
            valid_coverage=0.9,
            confidence=0.87,
        ),
        driver_state=DriverState(state="attentive", confidence=0.94),
    )

    restored = InferenceResponse.model_validate_json(response.model_dump_json())

    assert restored.detections[0].bounding_box.x_max == 110
    assert restored.driver_state is not None
    assert restored.driver_state.state == "attentive"
