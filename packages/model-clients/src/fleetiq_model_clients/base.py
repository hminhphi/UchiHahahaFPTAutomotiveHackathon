"""Shared typed interface for FleetIQ model inference adapters."""

from typing import Protocol

from fleetiq_contracts import InferenceRequest, InferenceResponse


class ModelClient(Protocol):
    """A model adapter that preserves the versioned FleetIQ boundary."""

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        """Run inference for one typed request."""
        ...
