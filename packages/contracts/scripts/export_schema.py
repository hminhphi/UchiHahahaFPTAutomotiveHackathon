"""Export the FleetIQ v1 JSON Schema collection used by protocol documentation."""

from __future__ import annotations

import json
from pathlib import Path

from fleetiq_contracts.base import EventEnvelope
from fleetiq_contracts.events import (
    CoachingAck,
    CoachingCommand,
    RiskEvent,
    TelemetryEvent,
)
from fleetiq_contracts.inference import InferenceRequest, InferenceResponse
from pydantic.json_schema import models_json_schema

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = ROOT / "docs" / "protocols" / "schemas" / "events-v1.json"


def main() -> None:
    """Write the schemas for all public v1 event and inference payloads."""
    models = (
        (EventEnvelope, "validation"),
        (TelemetryEvent, "validation"),
        (RiskEvent, "validation"),
        (CoachingCommand, "validation"),
        (CoachingAck, "validation"),
        (InferenceRequest, "validation"),
        (InferenceResponse, "validation"),
    )
    _, schema = models_json_schema(models, title="FleetIQ Protocols v1")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
