"""Standard-library JSON logging with FleetIQ redaction."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

from .redaction import redact


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class JsonFormatter(logging.Formatter):
    """Serialize a log record and its optional ``fleetiq`` fields as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _utc_timestamp(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = getattr(record, "fleetiq", None)
        if isinstance(fields, dict):
            payload.update(redact(fields))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(redact(payload), ensure_ascii=True, separators=(",", ":"))


def configure_json_logging(
    level: int = logging.INFO,
    *,
    logger: logging.Logger | None = None,
    stream: TextIO | None = None,
) -> logging.Handler:
    """Attach one JSON handler without replacing application-owned handlers."""
    target = logger or logging.getLogger()
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.setLevel(level)
    target.setLevel(level)
    target.addHandler(handler)
    return handler
