from datetime import UTC, datetime
from uuid import uuid4

from fleetiq_coaching.policy import CoachingPolicy
from fleetiq_contracts import RiskEvent


def risk(severity: int) -> RiskEvent:
    return RiskEvent(
        schema_version="1.0",
        event_id=uuid4(),
        correlation_id="correlation-1",
        trip_id="T01-Sample",
        frame_index=10,
        producer="fusion-worker",
        occurred_at=datetime.now(UTC),
        event_type="compound_risk",
        severity=severity,
        confidence=0.9,
        explanation="short_ttc, driver_distraction, compound_risk",
    )


def test_critical_coaching_is_short_and_immediate() -> None:
    command = CoachingPolicy().command_for(risk(5), vehicle_id="vehicle-1")

    assert command is not None
    assert command.channel == "visual"
    assert command.priority == 5
    assert len(command.message.split()) <= 8


def test_low_risk_does_not_interrupt_driver() -> None:
    assert CoachingPolicy().command_for(risk(1), vehicle_id="vehicle-1") is None
