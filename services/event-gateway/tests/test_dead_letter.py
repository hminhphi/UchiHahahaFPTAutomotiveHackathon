import hashlib
import json

from fleetiq_event_gateway.handler import EventHandler
from test_handler import FakeTransport


def test_invalid_risk_payload_goes_to_dead_letter() -> None:
    transport = FakeTransport()
    handler = EventHandler(transport)

    handler.handle("fleetiq/v1/trips/T01-Sample/risk", b'{"severity":99}')

    published = transport.published[0]
    assert published.topic == "fleetiq/v1/dead-letter/event-gateway"
    assert published.qos == 1
    assert published.retain is False


def test_dead_letter_does_not_echo_untrusted_payload() -> None:
    transport = FakeTransport()
    handler = EventHandler(transport)
    payload = b'{"authorization":"Bearer secret"}'

    handler.handle("fleetiq/v1/trips/T01-Sample/risk", payload)

    body = json.loads(transport.published[0].payload)
    serialized = json.dumps(body)
    assert "Bearer secret" not in serialized
    assert body["payload_sha256"] == hashlib.sha256(payload).hexdigest()
    assert body["payload_size"] == len(payload)


def test_unknown_topic_goes_to_dead_letter() -> None:
    transport = FakeTransport()
    handler = EventHandler(transport)

    handler.handle("fleetiq/v1/unknown", b"{}")

    body = json.loads(transport.published[0].payload)
    assert body["error_code"] == "unsupported_topic"
