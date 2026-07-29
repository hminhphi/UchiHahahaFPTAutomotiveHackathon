"""Bounded CarSky HTTPS adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx
from fleetiq_contracts import CoachingCommand
from fleetiq_contracts.base import validate_mqtt_segment
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CarSkySettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    base_url: str
    api_key: str = Field(min_length=1)
    room_id: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    connect_timeout_s: float = Field(default=3.0, gt=0, le=30)
    read_timeout_s: float = Field(default=5.0, gt=0, le=60)

    @model_validator(mode="after")
    def validate_base_url(self) -> CarSkySettings:
        parsed = urlsplit(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("CARSKY_BASE_URL must be an HTTPS URL without query or fragment")
        return self

    @field_validator("room_id", "node_key")
    @classmethod
    def validate_path_identifier(cls, value: str) -> str:
        return validate_mqtt_segment(value)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> CarSkySettings:
        required = {
            "base_url": "CARSKY_BASE_URL",
            "api_key": "CARSKY_API_KEY",
            "room_id": "CARSKY_ROOM_ID",
            "node_key": "CARSKY_NODE_KEY",
        }
        missing = [name for name in required.values() if not environment.get(name)]
        if missing:
            raise ValueError(f"missing CarSky settings: {', '.join(missing)}")
        return cls(**{field: environment[name] for field, name in required.items()})


class HttpClient(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any: ...


class MockCarSkyAdapter:
    def __init__(self) -> None:
        self.delivered: list[CoachingCommand] = []

    def deliver(self, command: CoachingCommand) -> None:
        self.delivered.append(command.model_copy(deep=True))


class CarSkyAdapter:
    def __init__(
        self,
        settings: CarSkySettings,
        *,
        client: HttpClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.Client()
        self._timeout = httpx.Timeout(
            connect=settings.connect_timeout_s,
            read=settings.read_timeout_s,
            write=settings.read_timeout_s,
            pool=settings.connect_timeout_s,
        )

    def deliver(self, command: CoachingCommand) -> None:
        url = (
            f"{self._settings.base_url.rstrip('/')}/api/rooms/"
            f"{self._settings.room_id}/nodes/{self._settings.node_key}/commands"
        )
        failed = False
        try:
            response = self._client.post(
                url,
                json=command.model_dump(mode="json"),
                headers={
                    "X-API-Key": self._settings.api_key,
                    "Idempotency-Key": command.dedupe_key,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except Exception:  # noqa: BLE001 - external client boundary
            failed = True
        if failed:
            raise RuntimeError("CarSky delivery failed")
