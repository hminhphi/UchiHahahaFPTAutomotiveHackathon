"""Strict environment configuration for the MQTT gateway."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


class GatewaySettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    broker_host: str = Field(min_length=1)
    broker_port: int = Field(default=1883, ge=1, le=65535)
    use_tls: bool = False
    username: str | None = None
    password: str | None = None
    client_id: str = "fleetiq-event-gateway"
    keepalive_seconds: int = Field(default=30, ge=5, le=300)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "GatewaySettings":
        def boolean(name: str, default: bool) -> bool:
            raw = environment.get(name)
            if raw is None:
                return default
            normalized = raw.strip().casefold()
            if normalized in {"1", "true", "yes"}:
                return True
            if normalized in {"0", "false", "no"}:
                return False
            raise ValueError(f"{name} must be true or false")

        username = environment.get("FLEETIQ_MQTT_USERNAME")
        password = environment.get("FLEETIQ_MQTT_PASSWORD")
        if password and not username:
            raise ValueError("FLEETIQ_MQTT_USERNAME is required when password is set")
        return cls(
            broker_host=environment.get("FLEETIQ_MQTT_HOST", "mosquitto"),
            broker_port=int(environment.get("FLEETIQ_MQTT_PORT", "1883")),
            use_tls=boolean("FLEETIQ_MQTT_TLS", False),
            username=username,
            password=password,
            client_id=environment.get("FLEETIQ_MQTT_CLIENT_ID", "fleetiq-event-gateway"),
            keepalive_seconds=int(environment.get("FLEETIQ_MQTT_KEEPALIVE_SECONDS", "30")),
        )
