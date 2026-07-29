"""Transport-independent MQTT validation and routing."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from fleetiq_contracts import (
    CoachingAck,
    CoachingCommand,
    RiskEvent,
    TelemetryEvent,
    TopicRegistry,
)
from fleetiq_contracts.base import ContractModel
from pydantic import ValidationError


class Publisher(Protocol):
    def publish(self, topic: str, payload: bytes, *, qos: int, retain: bool) -> None: ...


_ROUTES: tuple[tuple[re.Pattern[str], type[ContractModel], str | None], ...] = (
    (re.compile(r"^fleetiq/v1/trips/([^/]+)/risk$"), RiskEvent, "trip_id"),
    (re.compile(r"^fleetiq/v1/vehicles/([^/]+)/telemetry$"), TelemetryEvent, None),
    (
        re.compile(r"^fleetiq/v1/vehicles/([^/]+)/coaching/command$"),
        CoachingCommand,
        "vehicle_id",
    ),
    (
        re.compile(r"^fleetiq/v1/vehicles/([^/]+)/coaching/ack$"),
        CoachingAck,
        "vehicle_id",
    ),
)


class EventHandler:
    def __init__(
        self,
        transport: Publisher,
        *,
        dispatch: Callable[[ContractModel], None] | None = None,
    ) -> None:
        self._transport = transport
        self._dispatch = dispatch or (lambda event: None)

    def handle(self, topic: str, payload: bytes) -> None:
        for pattern, model, identity_field in _ROUTES:
            match = pattern.fullmatch(topic)
            if match is None:
                continue
            try:
                event = model.model_validate_json(payload)
            except (ValidationError, ValueError, UnicodeDecodeError):
                self._dead_letter(topic, payload, "invalid_payload")
                return
            if identity_field is not None and getattr(event, identity_field) != match.group(1):
                self._dead_letter(topic, payload, "topic_identity_mismatch")
                return
            self._dispatch(event)
            return
        self._dead_letter(topic, payload, "unsupported_topic")

    def publish_telemetry(self, vehicle_id: str, event: TelemetryEvent) -> None:
        self._publish(TopicRegistry.telemetry(vehicle_id), event, qos=0)

    def publish_risk(self, event: RiskEvent) -> None:
        self._publish(TopicRegistry.risk(event.trip_id), event, qos=1)

    def publish_coaching(self, command: CoachingCommand) -> None:
        self._publish(
            TopicRegistry.coaching_command(command.vehicle_id),
            command,
            qos=1,
        )

    def publish_ack(self, acknowledgement: CoachingAck) -> None:
        self._publish(
            TopicRegistry.coaching_ack(acknowledgement.vehicle_id),
            acknowledgement,
            qos=1,
        )

    def publish_status(self, status: str) -> None:
        if status not in {"online", "degraded", "offline"}:
            raise ValueError("unsupported gateway status")
        payload = json.dumps(
            {
                "schema_version": "1.0",
                "service": "event-gateway",
                "status": status,
                "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
            separators=(",", ":"),
        ).encode()
        self._transport.publish(
            TopicRegistry.service_status("event-gateway"),
            payload,
            qos=1,
            retain=True,
        )

    def _publish(self, topic: str, event: ContractModel, *, qos: int) -> None:
        self._transport.publish(
            topic,
            event.model_dump_json().encode(),
            qos=qos,
            retain=False,
        )

    def _dead_letter(self, source_topic: str, payload: bytes, error_code: str) -> None:
        body = json.dumps(
            {
                "schema_version": "1.0",
                "source": "event-gateway",
                "source_topic": source_topic,
                "error_code": error_code,
                "payload_size": len(payload),
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode()
        self._transport.publish(
            TopicRegistry.dead_letter("event-gateway"),
            body,
            qos=1,
            retain=False,
        )
