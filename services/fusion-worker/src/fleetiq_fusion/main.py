"""JSONL entry point for deterministic fusion."""

import json
import sys

from fleetiq_contracts import InferenceResponse, TelemetryEvent

from .worker import FusionWorker


def main() -> None:
    worker = FusionWorker()
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        payload = json.loads(line)
        road = InferenceResponse.model_validate_json(json.dumps(payload["road"]))
        dms = InferenceResponse.model_validate_json(json.dumps(payload["dms"]))
        telemetry = TelemetryEvent.model_validate_json(json.dumps(payload["telemetry"]))
        sys.stdout.write(worker.fuse(road, dms, telemetry).model_dump_json() + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
