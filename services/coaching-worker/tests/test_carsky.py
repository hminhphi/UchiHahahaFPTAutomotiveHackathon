from dataclasses import dataclass, field
from typing import Any

import pytest
from fleetiq_coaching.carsky import CarSkyAdapter, CarSkySettings, MockCarSkyAdapter
from fleetiq_coaching.worker import CoachingWorker
from test_policy import risk


@dataclass
class FakeResponse:
    status_code: int = 202

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("authorization=secret")


@dataclass
class FakeHttpClient:
    calls: list[dict[str, Any]] = field(default_factory=list)
    response: FakeResponse = field(default_factory=FakeResponse)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response


def test_worker_does_not_deliver_same_dedupe_key_twice() -> None:
    adapter = MockCarSkyAdapter()
    worker = CoachingWorker(adapter)

    first = worker.process(risk(5), vehicle_id="vehicle-1")
    second = worker.process(risk(5), vehicle_id="vehicle-1")

    assert first.status == "accepted"
    assert second.status == "accepted"
    assert len(adapter.delivered) == 1


def test_real_adapter_uses_bounded_timeout_and_no_api_key_in_url() -> None:
    client = FakeHttpClient()
    settings = CarSkySettings(
        base_url="https://carsky.example",
        api_key="top-secret",
        room_id="room-1",
        node_key="node-1",
        connect_timeout_s=2.0,
        read_timeout_s=4.0,
    )
    adapter = CarSkyAdapter(settings, client=client)
    command = CoachingWorker(MockCarSkyAdapter()).policy.command_for(
        risk(5),
        vehicle_id="vehicle-1",
    )

    adapter.deliver(command)

    call = client.calls[0]
    assert "top-secret" not in call["url"]
    assert call["headers"]["X-API-Key"] == "top-secret"
    assert call["headers"]["Idempotency-Key"] == command.dedupe_key
    assert call["timeout"].connect == 2.0
    assert call["timeout"].read == 4.0


def test_real_adapter_sanitizes_delivery_errors() -> None:
    client = FakeHttpClient(response=FakeResponse(status_code=500))
    adapter = CarSkyAdapter(
        CarSkySettings(
            base_url="https://carsky.example",
            api_key="top-secret",
            room_id="room-1",
            node_key="node-1",
        ),
        client=client,
    )
    command = CoachingWorker(MockCarSkyAdapter()).policy.command_for(
        risk(5),
        vehicle_id="vehicle-1",
    )

    with pytest.raises(RuntimeError, match="CarSky delivery failed") as captured:
        adapter.deliver(command)

    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


@pytest.mark.parametrize("field", ["room_id", "node_key"])
def test_real_adapter_rejects_unsafe_path_identifiers(field: str) -> None:
    values = {
        "base_url": "https://carsky.example",
        "api_key": "top-secret",
        "room_id": "room-1",
        "node_key": "node-1",
    }
    values[field] = "../escape"

    with pytest.raises(ValueError):
        CarSkySettings(**values)
