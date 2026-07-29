import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from fleetiq_contracts import CoachingCommand, RiskEvent, TelemetryEvent
from fleetiq_event_gateway.handler import EventHandler


@dataclass(frozen=True)
class Published:
    topic: str
    payload: bytes
    qos: int
    retain: bool


@dataclass
class FakeTransport:
    published: list[Published] = field(default_factory=list)

    def publish(self, topic: str, payload: bytes, *, qos: int, retain: bool) -> None:
        self.published.append(Published(topic, payload, qos, retain))


def telemetry_event() -> TelemetryEvent:
    return TelemetryEvent(
        schema_version="1.0",
        event_id="telemetry-1",
        correlation_id="correlation-1",
        trip_id="T01-Sample",
        frame_index=1,
        producer="telemetry-worker",
        occurred_at=datetime.now(UTC),
        event_type="vehicle_state",
        speed_mps=10.0,
    )


def risk_event() -> RiskEvent:
    return RiskEvent(
        schema_version="1.0",
        event_id=uuid4(),
        correlation_id="correlation-1",
        trip_id="T01-Sample",
        frame_index=1,
        producer="roadface-worker",
        occurred_at=datetime.now(UTC),
        event_type="short_ttc",
        severity=4,
        confidence=0.9,
        explanation="Closing quickly",
    )


def coaching_command() -> CoachingCommand:
    now = datetime.now(UTC)
    return CoachingCommand(
        schema_version="1.0",
        command_id=uuid4(),
        event_id=uuid4(),
        correlation_id="correlation-1",
        vehicle_id="vehicle-1",
        created_at=now,
        expires_at=now,
        channel="visual",
        priority=3,
        title="Slow down",
        message="Increase following distance",
        dedupe_key="coach-1",
    )


def test_valid_risk_payload_dispatches_typed_event() -> None:
    transport = FakeTransport()
    dispatched: list[object] = []
    event = risk_event()
    handler = EventHandler(transport, dispatch=dispatched.append)

    handler.handle("fleetiq/v1/trips/T01-Sample/risk", event.model_dump_json().encode())

    assert dispatched == [event]
    assert transport.published == []


def test_topic_identity_mismatch_goes_to_dead_letter() -> None:
    transport = FakeTransport()
    handler = EventHandler(transport)

    handler.handle(
        "fleetiq/v1/trips/T02-Sample/risk",
        risk_event().model_dump_json().encode(),
    )

    assert transport.published[0].topic == "fleetiq/v1/dead-letter/event-gateway"
    body = json.loads(transport.published[0].payload)
    assert body["error_code"] == "topic_identity_mismatch"


def test_publish_helpers_apply_protocol_qos_and_retain_policy() -> None:
    transport = FakeTransport()
    handler = EventHandler(transport)

    handler.publish_telemetry("vehicle-1", telemetry_event())
    handler.publish_risk(risk_event())
    handler.publish_coaching(coaching_command())
    handler.publish_status("online")

    assert [(item.qos, item.retain) for item in transport.published] == [
        (0, False),
        (1, False),
        (1, False),
        (1, True),
    ]
    assert transport.published[-1].topic == "fleetiq/v1/services/event-gateway/status"
