"""Validated SageMaker endpoint selection and bounded runtime settings."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class EndpointKind(StrEnum):
    """FleetIQ model roles hosted as independent SageMaker endpoints."""

    DETECTOR = "detector"
    DEPTH = "depth"
    LANE = "lane"
    DMS = "dms"


ENDPOINT_ENVIRONMENT_VARIABLES: dict[EndpointKind, str] = {
    EndpointKind.DETECTOR: "SAGEMAKER_DETECTOR_ENDPOINT",
    EndpointKind.DEPTH: "SAGEMAKER_DEPTH_ENDPOINT",
    EndpointKind.LANE: "SAGEMAKER_LANE_ENDPOINT",
    EndpointKind.DMS: "SAGEMAKER_DMS_ENDPOINT",
}

_ENDPOINT_NAME = re.compile(r"^[A-Za-z0-9](?:-*[A-Za-z0-9])*$")


def validate_endpoint_name(value: str) -> str:
    """Validate the documented SageMaker endpoint-name shape."""
    if len(value) > 63 or _ENDPOINT_NAME.fullmatch(value) is None:
        raise ValueError("SageMaker endpoint name is invalid")
    return value


@dataclass(frozen=True, slots=True)
class SageMakerEndpointSettings:
    """One selected endpoint plus conservative botocore network bounds."""

    endpoint_name: str
    connect_timeout_s: int = 3
    read_timeout_s: int = 30
    total_max_attempts: int = 3

    def __post_init__(self) -> None:
        validate_endpoint_name(self.endpoint_name)
        if self.connect_timeout_s <= 0 or self.read_timeout_s <= 0:
            raise ValueError("SageMaker timeouts must be positive")
        if not 1 <= self.total_max_attempts <= 3:
            raise ValueError("SageMaker total attempts must be between one and three")

    @classmethod
    def from_environment(
        cls,
        kind: EndpointKind,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "SageMakerEndpointSettings":
        """Load one role-specific endpoint without an implicit fallback."""
        source = os.environ if environ is None else environ
        variable = ENDPOINT_ENVIRONMENT_VARIABLES[kind]
        endpoint_name = source.get(variable)
        if endpoint_name is None or not endpoint_name.strip():
            raise ValueError(f"{variable} is required")
        if endpoint_name != endpoint_name.strip():
            raise ValueError(f"{variable} must not contain surrounding whitespace")
        return cls(endpoint_name=endpoint_name)
