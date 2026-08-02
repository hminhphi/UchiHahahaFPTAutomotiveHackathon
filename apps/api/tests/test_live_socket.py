import asyncio
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from fleetiq_api.dependencies import InMemoryCameraFrameSink, InMemoryLatestStateBroker, create_test_dependencies
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


def test_camera_socket_broadcasts_producer_frame_to_viewer() -> None:
    app = create_app(testing=True)
    packet = _camera_packet(11)

    with (
        TestClient(app) as client,
        client.websocket_connect("/ws/v1/trips/T01/camera/road_left") as viewer,
        client.websocket_connect("/ws/v1/trips/T01/camera/road_left") as producer,
    ):
        producer.send_bytes(packet)
        assert producer.receive_json()["frame_index"] == 11
        assert viewer.receive_bytes() == packet


def test_camera_socket_producer_role_does_not_receive_cached_frame() -> None:
    dependencies = create_test_dependencies()
    app = create_app(testing=True, dependencies=dependencies)

    with (
        TestClient(app) as client,
        client.websocket_connect("/ws/v1/trips/T01/camera/road_left") as viewer,
    ):
        viewer.send_bytes(_camera_packet(12))
        assert viewer.receive_json()["frame_index"] == 12

    with (
        TestClient(app) as client,
        client.websocket_connect(
            "/ws/v1/trips/T01/camera/road_left?role=producer"
        ) as producer,
    ):
        producer.send_bytes(_camera_packet(13))
        acknowledgement = producer.receive_json()

    assert acknowledgement["frame_index"] == 13


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


def test_camera_frame_subscriber_receives_published_binary_packet() -> None:
    async def scenario() -> tuple[bytes, bool]:
        sink = InMemoryCameraFrameSink()
        subscription = await sink.subscribe("T01", "road_left")
        packet = _camera_packet(4)
        await sink.publish("T01", "road_left", packet)
        received = await asyncio.wait_for(subscription.queue.get(), timeout=0.5)
        await subscription.close()
        return received, subscription.closed

    received, closed = asyncio.run(scenario())

    assert received == _camera_packet(4)
    assert closed is True


def test_camera_frame_publish_can_exclude_source_subscriber() -> None:
    async def scenario() -> tuple[bytes, bool]:
        sink = InMemoryCameraFrameSink()
        producer = await sink.subscribe("T01", "road_left")
        viewer = await sink.subscribe("T01", "road_left")
        packet = _camera_packet(5)
        await sink.publish("T01", "road_left", packet, exclude=producer.queue)
        received = await asyncio.wait_for(viewer.queue.get(), timeout=0.5)
        source_empty = producer.queue.empty()
        await producer.close()
        await viewer.close()
        return received, source_empty

    received, source_empty = asyncio.run(scenario())

    assert received == _camera_packet(5)
    assert source_empty is True


def test_camera_frame_subscriber_starts_with_a_clean_replay_queue() -> None:
    async def scenario() -> bool:
        sink = InMemoryCameraFrameSink()
        await sink.publish("T01", "road_left", _camera_packet(99))
        subscription = await sink.subscribe("T01", "road_left")
        queue_is_empty = subscription.queue.empty()
        await subscription.close()
        return queue_is_empty

    assert asyncio.run(scenario()) is True
