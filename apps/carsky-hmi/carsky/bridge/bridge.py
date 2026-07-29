"""Bounded in-room coaching bridge for the CarSky Android guest."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import RLock
from urllib.parse import parse_qs, urlsplit

LOGGER = logging.getLogger("fleetiq.carsky.bridge")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ROUTE_IDENTIFIER = r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"


class InvalidCommand(ValueError):
    """Raised when a coaching command is unsafe to display."""


@dataclass(frozen=True, slots=True)
class StoredCommand:
    schema_version: str
    command_id: str
    vehicle_id: str
    severity: int
    title: str
    message: str
    dedupe_key: str
    expires_at: str
    acknowledged: bool = False


class CoachingStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._by_id: dict[str, StoredCommand] = {}
        self._by_dedupe: dict[str, StoredCommand] = {}
        self._latest_by_vehicle: dict[str, StoredCommand] = {}

    @property
    def command_count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def accept(self, payload: dict[str, object]) -> StoredCommand:
        command = _parse_command(payload)
        with self._lock:
            duplicate = self._by_dedupe.get(command.dedupe_key)
            if duplicate is not None:
                return duplicate
            self._by_id[command.command_id] = command
            self._by_dedupe[command.dedupe_key] = command
            self._latest_by_vehicle[command.vehicle_id] = command
            return command

    def current(self, vehicle_id: str) -> StoredCommand | None:
        _validate_identifier("vehicle_id", vehicle_id)
        with self._lock:
            command = self._latest_by_vehicle.get(vehicle_id)
            if command is not None and _parse_datetime(
                command.expires_at
            ) <= datetime.now(UTC):
                return None
            return command

    def acknowledge(self, command_id: str) -> StoredCommand:
        _validate_identifier("command_id", command_id)
        with self._lock:
            current = self._by_id.get(command_id)
            if current is None:
                raise KeyError(command_id)
            acknowledged = replace(current, acknowledged=True)
            self._by_id[command_id] = acknowledged
            self._by_dedupe[acknowledged.dedupe_key] = acknowledged
            self._latest_by_vehicle[acknowledged.vehicle_id] = acknowledged
            return acknowledged


def _parse_command(payload: dict[str, object]) -> StoredCommand:
    required = (
        "schema_version",
        "command_id",
        "vehicle_id",
        "priority",
        "title",
        "message",
        "dedupe_key",
        "expires_at",
    )
    if any(field not in payload for field in required):
        raise InvalidCommand("missing required coaching field")
    if payload["schema_version"] != "1.0":
        raise InvalidCommand("unsupported schema version")
    priority = payload["priority"]
    if (
        isinstance(priority, bool)
        or not isinstance(priority, int)
        or priority not in range(1, 6)
    ):
        raise InvalidCommand("priority must be between 1 and 5")
    values = {field: payload[field] for field in required if field != "priority"}
    if not all(isinstance(value, str) for value in values.values()):
        raise InvalidCommand("coaching text fields must be strings")
    command_id = _validate_identifier("command_id", str(payload["command_id"]))
    vehicle_id = _validate_identifier("vehicle_id", str(payload["vehicle_id"]))
    dedupe_key = _validate_identifier("dedupe_key", str(payload["dedupe_key"]))
    title = str(payload["title"]).strip()
    message = str(payload["message"]).strip()
    expires_at = str(payload["expires_at"])
    _parse_datetime(expires_at)
    if not title or len(title) > 48:
        raise InvalidCommand("title must contain 1 to 48 characters")
    if not message or len(message) > 120:
        raise InvalidCommand("message must contain 1 to 120 characters")
    return StoredCommand(
        schema_version="1.0",
        command_id=command_id,
        vehicle_id=vehicle_id,
        severity=priority,
        title=title,
        message=message,
        dedupe_key=dedupe_key,
        expires_at=expires_at,
    )


def _validate_identifier(name: str, value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise InvalidCommand(f"invalid {name}")
    return value


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise InvalidCommand("invalid expires_at") from error
    if parsed.tzinfo is None:
        raise InvalidCommand("expires_at must include a timezone")
    return parsed.astimezone(UTC)


def is_command_route(path: str) -> bool:
    if path == "/v1/coaching":
        return True
    pattern = rf"/api/rooms/{ROUTE_IDENTIFIER}/nodes/{ROUTE_IDENTIFIER}/commands"
    return re.fullmatch(pattern, path) is not None


STORE = CoachingStore()


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "FleetIQCarSkyBridge/1.0"

    def do_GET(self) -> None:
        route = urlsplit(self.path)
        if route.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
            return
        if route.path == "/v1/coaching/current":
            vehicle_id = parse_qs(route.query).get("vehicle_id", [""])[0]
            try:
                command = STORE.current(vehicle_id)
            except InvalidCommand:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid request"})
                return
            if command is None:
                self.send_response(HTTPStatus.NO_CONTENT)
                self.end_headers()
                return
            self._json(HTTPStatus.OK, asdict(command))
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        route = urlsplit(self.path)
        if is_command_route(route.path):
            try:
                command = STORE.accept(self._read_json())
            except (InvalidCommand, json.JSONDecodeError):
                self._json(
                    HTTPStatus.BAD_REQUEST, {"error": "invalid coaching command"}
                )
                return
            self._json(HTTPStatus.ACCEPTED, asdict(command))
            return
        match = re.fullmatch(
            r"/v1/coaching/([A-Za-z0-9][A-Za-z0-9._-]{0,127})/ack", route.path
        )
        if match:
            try:
                command = STORE.acknowledge(match.group(1))
            except KeyError:
                self._json(HTTPStatus.NOT_FOUND, {"error": "command not found"})
                return
            self._json(HTTPStatus.OK, asdict(command))
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 16_384:
            raise InvalidCommand("invalid content length")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise InvalidCommand("JSON object required")
        return value

    def _json(self, status: HTTPStatus, value: dict[str, object]) -> None:
        encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, message: str, *args: object) -> None:
        LOGGER.info(message, *args)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    host = os.getenv("BRIDGE_HOST", "0.0.0.0")
    port = int(os.getenv("BRIDGE_PORT", "8090"))
    LOGGER.info("starting CarSky bridge on %s:%d", host, port)
    ThreadingHTTPServer((host, port), BridgeHandler).serve_forever()


if __name__ == "__main__":
    main()
