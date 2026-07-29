"""Typed, bounded Amazon SageMaker realtime inference adapter."""

from collections.abc import Mapping
from typing import Any, Protocol, cast
from urllib.parse import quote

from fleetiq_contracts import InferenceRequest, InferenceResponse

from .config import EndpointKind, SageMakerEndpointSettings, validate_endpoint_name


class _ReadableBody(Protocol):
    def read(self) -> bytes:
        """Read the complete bounded SageMaker response body."""
        ...


class _RuntimeClient(Protocol):
    def invoke_endpoint(self, **kwargs: Any) -> Mapping[str, Any]:
        """Invoke one SageMaker realtime endpoint."""
        ...


class SageMakerInvocationError(RuntimeError):
    """A sanitized failure safe for worker logs."""


def _create_runtime_client(settings: SageMakerEndpointSettings) -> _RuntimeClient:
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        raise RuntimeError(
            "AWS support requires the fleetiq-model-clients[aws] extra"
        ) from None

    config = Config(
        connect_timeout=settings.connect_timeout_s,
        read_timeout=settings.read_timeout_s,
        retries={
            "mode": "standard",
            "total_max_attempts": settings.total_max_attempts,
        },
    )
    return cast(
        _RuntimeClient,
        boto3.client("sagemaker-runtime", config=config),
    )


def _validate_media_type(value: str, *, field: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) > 126 for character in value)
    ):
        raise ValueError(f"{field} must be a visible ASCII media type")
    return value


def _validate_custom_attributes(value: str) -> str:
    if (
        not value
        or len(value.encode("ascii", errors="ignore")) != len(value)
        or len(value) > 1024
        or any(ord(character) < 32 or ord(character) > 126 for character in value)
    ):
        raise ValueError("custom_attributes must be 1-1024 visible ASCII characters")
    return value


class SageMakerModelClient:
    """Invoke one configured endpoint and validate its versioned response."""

    def __init__(
        self,
        endpoint_name: str,
        *,
        runtime_client: _RuntimeClient | None = None,
        accept: str = "application/json",
    ) -> None:
        self.endpoint_name = validate_endpoint_name(endpoint_name)
        self._accept = _validate_media_type(accept, field="accept")
        if runtime_client is None:
            settings = SageMakerEndpointSettings(endpoint_name=self.endpoint_name)
            runtime_client = _create_runtime_client(settings)
        self._runtime_client = runtime_client

    @classmethod
    def from_environment(
        cls,
        kind: EndpointKind,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "SageMakerModelClient":
        """Create an AWS runtime client for one explicitly named model role."""
        settings = SageMakerEndpointSettings.from_environment(kind, environ=environ)
        return cls(
            settings.endpoint_name,
            runtime_client=_create_runtime_client(settings),
        )

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        """Send the complete versioned request as endpoint JSON."""
        correlation = quote(request.correlation_id, safe="")
        return self.infer_bytes(
            request.model_dump_json().encode("utf-8"),
            content_type="application/json",
            custom_attributes=f"correlation-id={correlation}",
        )

    def infer_bytes(
        self,
        body: bytes,
        *,
        content_type: str,
        custom_attributes: str | None = None,
    ) -> InferenceResponse:
        """Send a direct JPEG/tensor payload and decode its typed response."""
        media_type = _validate_media_type(content_type, field="content_type")
        arguments: dict[str, Any] = {
            "EndpointName": self.endpoint_name,
            "Body": body,
            "ContentType": media_type,
            "Accept": self._accept,
        }
        if custom_attributes is not None:
            arguments["CustomAttributes"] = _validate_custom_attributes(
                custom_attributes
            )

        try:
            result = self._runtime_client.invoke_endpoint(**arguments)
        # SDK exception messages may contain signed URLs or request metadata.
        except Exception as error:  # noqa: BLE001
            error_type = type(error).__name__
            raise SageMakerInvocationError(
                f"SageMaker inference failed for endpoint "
                f"'{self.endpoint_name}' ({error_type})"
            ) from None

        return self._decode_response(result)

    def _decode_response(self, result: Mapping[str, Any]) -> InferenceResponse:
        try:
            response_body = result["Body"]
            if hasattr(response_body, "read"):
                payload = cast(_ReadableBody, response_body).read()
            else:
                payload = response_body
            if not isinstance(payload, bytes):
                raise TypeError("SageMaker response body must be bytes")
            return InferenceResponse.model_validate_json(payload)
        # Streaming and validation failures cross an untrusted response boundary.
        except Exception:  # noqa: BLE001
            raise SageMakerInvocationError(
                f"SageMaker endpoint '{self.endpoint_name}' returned an "
                "invalid InferenceResponse"
            ) from None
