"""DMS worker environment configuration."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DmsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    endpoint_name: str = Field(min_length=1)
    window_size: int = Field(default=5, ge=1, le=101)
    min_votes: int = Field(default=3, ge=1)

    @model_validator(mode="after")
    def validate_votes(self) -> "DmsSettings":
        if self.min_votes > self.window_size:
            raise ValueError("minimum votes cannot exceed the smoothing window")
        return self

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "DmsSettings":
        endpoint = environment.get("SAGEMAKER_DMS_ENDPOINT")
        if not endpoint:
            raise ValueError("SAGEMAKER_DMS_ENDPOINT is required")
        return cls(
            endpoint_name=endpoint,
            window_size=int(environment.get("FLEETIQ_DMS_WINDOW_SIZE", "5")),
            min_votes=int(environment.get("FLEETIQ_DMS_MIN_VOTES", "3")),
        )
