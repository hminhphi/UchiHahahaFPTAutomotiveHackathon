import json
from pathlib import Path

import pytest
from fleetiq_contracts.base import EventEnvelope
from fleetiq_contracts.events import (
    CoachingAck,
    CoachingCommand,
    RiskEvent,
    TelemetryEvent,
)
from fleetiq_contracts.inference import InferenceRequest, InferenceResponse
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "protocols"
    / "schemas"
    / "events-v1.json"
)
VERSIONED_MODELS = (
    EventEnvelope,
    TelemetryEvent,
    RiskEvent,
    CoachingCommand,
    CoachingAck,
    InferenceRequest,
    InferenceResponse,
)


@pytest.fixture
def schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.fixture
def risk_event_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": "f993e723-485e-441a-b75d-0cfcf6b4eb1f",
        "correlation_id": "trip-01:frame-100",
        "trip_id": "T01-Sample",
        "frame_index": 100,
        "producer": "fusion-worker",
        "occurred_at": "2026-07-28T00:00:00Z",
        "event_type": "short_ttc",
        "severity": 4,
        "confidence": 0.91,
        "explanation": "TTC below 1.5 seconds",
        "evidence": [
            {
                "artifact_uri": "s3://fleetiq-evidence/T01-Sample/frames/000100.jpg",
                "frame_index": 100,
                "description": "Road-facing frame at minimum TTC",
            }
        ],
    }


def test_exported_schema_rejects_empty_payload(schema_validator: Draft202012Validator) -> None:
    """An unconstrained root would claim every JSON value is a FleetIQ payload."""
    with pytest.raises(ValidationError):
        schema_validator.validate({})


def test_exported_schema_validates_documented_risk_event(
    schema_validator: Draft202012Validator, risk_event_payload: dict[str, object]
) -> None:
    """The documented risk-event example must be valid against the shipped schema."""
    schema_validator.validate(risk_event_payload)


def test_exported_schema_rejects_malformed_risk_event(
    schema_validator: Draft202012Validator, risk_event_payload: dict[str, object]
) -> None:
    """A string severity must fail exactly as it does at the Pydantic boundary."""
    risk_event_payload["severity"] = "4"

    with pytest.raises(ValidationError):
        schema_validator.validate(risk_event_payload)


def test_every_versioned_model_requires_schema_version() -> None:
    """A defaulted version would allow unversioned payloads onto the wire."""
    for model in VERSIONED_MODELS:
        assert "schema_version" in model.model_json_schema()["required"]
