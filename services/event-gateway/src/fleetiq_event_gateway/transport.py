"""Paho MQTT transport; callbacks do no domain validation."""

from __future__ import annotations

from collections.abc import Callable

import paho.mqtt.client as mqtt

from .config import GatewaySettings


class PahoTransport:
    def __init__(
        self,
        settings: GatewaySettings,
        on_message: Callable[[str, bytes], None],
    ) -> None:
        self._settings = settings
        self._on_message = on_message
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.client_id,
        )
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message
        if settings.username is not None:
            self._client.username_pw_set(settings.username, settings.password)
        if settings.use_tls:
            self._client.tls_set()

    def connect(self) -> None:
        self._client.connect(
            self._settings.broker_host,
            self._settings.broker_port,
            self._settings.keepalive_seconds,
        )

    def loop_forever(self) -> None:
        self._client.loop_forever(retry_first_connection=True)

    def disconnect(self) -> None:
        self._client.disconnect()

    def publish(self, topic: str, payload: bytes, *, qos: int, retain: bool) -> None:
        result = self._client.publish(topic, payload, qos=qos, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed with code {result.rc}")

    def _handle_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            raise ConnectionError(f"MQTT connection failed with code {reason_code}")
        client.subscribe(
            [
                ("fleetiq/v1/vehicles/+/telemetry", 0),
                ("fleetiq/v1/trips/+/risk", 1),
                ("fleetiq/v1/vehicles/+/coaching/command", 1),
                ("fleetiq/v1/vehicles/+/coaching/ack", 1),
            ]
        )

    def _handle_message(
        self,
        client: mqtt.Client,
        userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        self._on_message(message.topic, bytes(message.payload))
