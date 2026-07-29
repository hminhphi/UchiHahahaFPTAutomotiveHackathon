"""JSONL process entry point for the DMS worker."""

import os
import sys

from fleetiq_contracts import InferenceRequest
from fleetiq_model_clients.sagemaker import SageMakerModelClient

from .config import DmsSettings
from .worker import DmsWorker


def main() -> None:
    settings = DmsSettings.from_environment(os.environ)
    worker = DmsWorker(
        SageMakerModelClient(settings.endpoint_name),
        window_size=settings.window_size,
        min_votes=settings.min_votes,
    )
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        request = InferenceRequest.model_validate_json(line)
        response = worker.process(request)
        sys.stdout.write(response.model_dump_json() + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
