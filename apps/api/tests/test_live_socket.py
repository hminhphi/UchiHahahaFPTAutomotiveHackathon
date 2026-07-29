import asyncio
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from fleetiq_api.dependencies import InMemoryLatestStateBroker, create_test_dependencies
from fleetiq_api.main import create_app


def _camera_packet(frame_index: int = 1) -> bytes:
    metadata = json.dumps(
        {
            "schema_version": "1.0",
            "frame_index": frame_index,
            "occurred_at": datetime(2026, 7, 29, 12, 0, tzinfo=UTC).isoformat(),
            "width": 640,
            "height": 360,
            "correlation_id": f"corr-{frame_index}",
        }
    ).encode("utf-8")
    return len(metadata).to_bytes(4, "big") + metadata + b"\xff\xd8jpeg\xff\xd9"


def test_camera_socket_accepts_binary_frame_and_returns_ack() -> None:
    dependencies = create_test_dependencies()
    app = create_app(testing=True, dependencies=dependencies)

    with (
        TestClient(app) as client,
        client.websocket_connect("/ws/v1/trips/T01/camera/left") as socket,
    ):
        socket.send_bytes(_camera_packet(9))
        acknowledgement = socket.receive_json()

    assert acknowledgement == {
        "schema_version": "1.0",
        "status": "accepted",
        "trip_id": "T01",
        "view": "left",
        "frame_index": 9,
        "correlation_id": "corr-9",
    }
    assert dependencies.camera_sink.latest[("T01", "left")].metadata.frame_index == 9


def test_camera_socket_closes_oversized_frame_with_1009() -> None:
    app = create_app(testing=True, max_frame_bytes=4)

    with (
        TestClient(app) as client,
        client.websocket_connect("/ws/v1/trips/T01/camera/left") as socket,
    ):
        socket.send_bytes(_camera_packet())
        message = socket.receive()

    assert message["type"] == "websocket.close"
    assert message["code"] == 1009


def test_camera_socket_rejects_text_payload() -> None:
    with (
        TestClient(create_app(testing=True)) as client,
        client.websocket_connect("/ws/v1/trips/T01/camera/left") as socket,
    ):
        socket.send_text("base64-is-not-allowed")
        message = socket.receive()

    assert message["type"] == "websocket.close"
    assert message["code"] == 1003


def test_live_socket_sends_current_latest_state_and_disconnects_cleanly() -> None:
    dependencies = create_test_dependencies()
    dependencies.live_state.publish_nowait(
        "T01",
        {"schema_version": "1.0", "trip_id": "T01", "frame_index": 12, "ttc_seconds": 2.4},
    )

    with (
        TestClient(create_app(testing=True, dependencies=dependencies)) as client,
        client.websocket_connect("/ws/v1/trips/T01/live") as socket,
    ):
        assert socket.receive_json()["frame_index"] == 12


def test_latest_state_subscription_drops_intermediate_backlog() -> None:
    async def scenario() -> tuple[dict[str, int], bool]:
        broker = InMemoryLatestStateBroker()
        subscription = await broker.subscribe("T01")
        broker.publish_nowait("T01", {"frame_index": 1})
        broker.publish_nowait("T01", {"frame_index": 2})
        broker.publish_nowait("T01", {"frame_index": 3})
        state = await subscription.queue.get()
        await subscription.close()
        return state, subscription.closed

    state, closed = asyncio.run(scenario())

    assert state == {"frame_index": 3}
    assert closed is True
