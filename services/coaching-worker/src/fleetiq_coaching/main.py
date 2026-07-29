"""JSONL entry point for CarSky coaching delivery."""

import json
import os
import sys

from fleetiq_contracts import RiskEvent

from .carsky import CarSkyAdapter, CarSkySettings
from .worker import CoachingWorker


def main() -> None:
    worker = CoachingWorker(
        CarSkyAdapter(CarSkySettings.from_environment(os.environ))
    )
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        payload = json.loads(line)
        event = RiskEvent.model_validate_json(json.dumps(payload["risk_event"]))
        acknowledgement = worker.process(event, vehicle_id=payload["vehicle_id"])
        output = None if acknowledgement is None else acknowledgement.model_dump(mode="json")
        sys.stdout.write(json.dumps(output, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
