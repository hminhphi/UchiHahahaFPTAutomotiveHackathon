"""Small local substitute for the SageMaker real-time inference HTTP contract."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY_BYTES = 1_048_576


class ModelMockHandler(BaseHTTPRequestHandler):
    server_version = "FleetIQModelMock/1.0"

    def do_GET(self) -> None:
        if self.path == "/ping":
            self._json(HTTPStatus.OK, {"status": "ok"})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/invocations":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            payload = self._read_json()
            trip_id = _required_text(payload, "trip_id")
            frame_index = _required_frame(payload)
            model = _required_text(payload, "model")
        except (TypeError, ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid inference request"})
            return
        self._json(
            HTTPStatus.OK,
            {
                "schema_version": "1.0",
                "trip_id": trip_id,
                "frame_index": frame_index,
                "model": model,
                "provider": "local-mock",
                "detections": [],
                "confidence": 1.0,
            },
        )

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("invalid content length")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise TypeError("JSON object required")
        return payload

    def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, message: str, *args: object) -> None:
        print(f"model-mock: {message % args}", flush=True)


def _required_text(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value


def _required_frame(payload: dict[str, object]) -> int:
    value = payload.get("frame_index")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("frame_index must be a non-negative integer")
    return value


def main() -> None:
    port = int(os.getenv("MODEL_MOCK_PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), ModelMockHandler).serve_forever()


if __name__ == "__main__":
    main()
