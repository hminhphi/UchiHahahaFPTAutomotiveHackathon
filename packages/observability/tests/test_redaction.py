import json
import logging

from fleetiq_observability import JsonFormatter, redact


def test_redact_removes_nested_credentials_and_presigned_queries() -> None:
    payload = {
        "authorization": "Bearer secret",
        "nested": {
            "api_key": "private-key",
            "credentials": {"password": "hunter2", "user": "fleet"},
            "items": [
                {
                    "artifact_url": (
                        "https://bucket.example/evidence.jpg"
                        "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=secret"
                    )
                }
            ],
        },
        "safe_url": "https://fleet.example/trips?view=summary",
    }

    assert redact(payload) == {
        "authorization": "[REDACTED]",
        "nested": {
            "api_key": "[REDACTED]",
            "credentials": "[REDACTED]",
            "items": [{"artifact_url": "https://bucket.example/evidence.jpg?[REDACTED]"}],
        },
        "safe_url": "https://fleet.example/trips?view=summary",
    }


def test_json_formatter_emits_redacted_structured_fields() -> None:
    record = logging.LogRecord(
        "fleetiq.test",
        logging.INFO,
        __file__,
        1,
        "request_complete",
        (),
        None,
    )
    record.fleetiq = {
        "request_id": "req-1",
        "headers": {"Authorization": "Bearer secret"},
    }

    output = json.loads(JsonFormatter().format(record))

    assert output["message"] == "request_complete"
    assert output["request_id"] == "req-1"
    assert output["headers"]["Authorization"] == "[REDACTED]"
    assert output["timestamp"].endswith("Z")


def test_redact_removes_presigned_query_embedded_in_exception_text() -> None:
    message = (
        "download failed for https://bucket.example/frame.jpg"
        "?X-Amz-Credential=private&X-Amz-Signature=secret"
    )

    assert redact(message) == "download failed for https://bucket.example/frame.jpg?[REDACTED]"
