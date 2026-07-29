"""Deterministic fixture-backed model adapter for local and test use."""

from pathlib import Path

from fleetiq_contracts import InferenceRequest, InferenceResponse


class LocalFixtureModelClient:
    """Return a validated fixture while preserving request trace fields."""

    def __init__(self, response: InferenceResponse) -> None:
        self._response = response

    @classmethod
    def from_fixture(cls, path: str | Path) -> "LocalFixtureModelClient":
        """Load and validate a response fixture without exposing bad contents."""
        try:
            payload = Path(path).read_bytes()
            response = InferenceResponse.model_validate_json(payload)
        except (OSError, ValueError):
            raise ValueError("invalid InferenceResponse fixture") from None
        return cls(response)

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        """Return fixture model output correlated to the typed request."""
        values = self._response.model_dump()
        values.update(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            trip_id=request.trip_id,
            frame_index=request.frame_index,
            occurred_at=request.occurred_at,
        )
        return InferenceResponse.model_validate(values)

    def infer_bytes(
        self,
        body: bytes,
        *,
        content_type: str,
        custom_attributes: str | None = None,
    ) -> InferenceResponse:
        """Return an isolated copy for any equivalent local binary payload."""
        del body, content_type, custom_attributes
        return self._response.model_copy(deep=True)
