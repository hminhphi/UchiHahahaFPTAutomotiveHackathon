"""Protocol-level smoke test for the local FleetIQ full profile."""

from __future__ import annotations

import json
import os
import struct
import threading
import time
from datetime import UTC, datetime, timedelta
from urllib.request import Request, urlopen
from uuid import uuid4

import paho.mqtt.client as mqtt
from websockets.sync.client import connect

API_URL = os.getenv("FLEETIQ_SMOKE_API_URL", "http://localhost:8000")
MODEL_URL = os.getenv("FLEETIQ_SMOKE_MODEL_URL", "http://localhost:8080")
BRIDGE_URL = os.getenv("FLEETIQ_SMOKE_BRIDGE_URL", "http://localhost:8090")
MQTT_HOST = os.getenv("FLEETIQ_SMOKE_MQTT_HOST", "localhost")
WS_URL = os.getenv("FLEETIQ_SMOKE_WS_URL", "ws://localhost:8000")


def http_json(
    url: str, *, payload: dict[str, object] | None = None
) -> tuple[int, object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="GET" if body is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        content = response.read()
        return response.status, None if not content else json.loads(content)


def wait_ready() -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            status, payload = http_json(f"{API_URL}/health/ready")
            if status == 200 and payload["status"] == "ok":
                return
        except (OSError, KeyError, TypeError):
            pass
        time.sleep(0.5)
    raise RuntimeError("API readiness timed out")


def mqtt_round_trip() -> None:
    received = threading.Event()
    subscribed = threading.Event()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fleetiq-smoke")
    client.on_message = lambda _client, _userdata, _message: received.set()
    client.on_subscribe = lambda _client, _userdata, _mid, _codes, _properties: (
        subscribed.set()
    )
    client.connect(MQTT_HOST, 1883, 10)
    client.subscribe("fleetiq/v1/trips/T01-Sample/risk", qos=1)
    client.loop_start()
    try:
        if not subscribed.wait(5):
            raise RuntimeError("risk subscription was not acknowledged")
        now = datetime.now(UTC).isoformat()
        telemetry = {
            "schema_version": "1.0",
            "event_id": str(uuid4()),
            "correlation_id": "smoke-correlation",
            "trip_id": "T01-Sample",
            "frame_index": 1,
            "producer": "compose-smoke",
            "occurred_at": now,
            "event_type": "vehicle_state",
            "speed_mps": 12.0,
            "longitudinal_accel_mps2": 0.1,
            "lateral_accel_mps2": 0.0,
            "yaw_rate_radps": 0.0,
        }
        client.publish(
            "fleetiq/v1/vehicles/vehicle-1/telemetry",
            json.dumps(telemetry),
            qos=1,
        ).wait_for_publish()
        risk = {
            "schema_version": "1.0",
            "event_id": str(uuid4()),
            "correlation_id": "smoke-correlation",
            "trip_id": "T01-Sample",
            "frame_index": 1,
            "producer": "compose-smoke",
            "occurred_at": now,
            "event_type": "short_ttc",
            "severity": 4,
            "confidence": 0.9,
            "explanation": "compose smoke risk",
        }
        client.publish("fleetiq/v1/trips/T01-Sample/risk", json.dumps(risk), qos=1)
        if not received.wait(5):
            raise RuntimeError("risk event was not received")
    finally:
        client.loop_stop()
        client.disconnect()


def model_inference() -> None:
    status, payload = http_json(
        f"{MODEL_URL}/invocations",
        payload={"trip_id": "T01-Sample", "frame_index": 1, "model": "roadface"},
    )
    if status != 200 or payload["schema_version"] != "1.0":
        raise RuntimeError("model mock failed")


def camera_websocket() -> None:
    metadata = json.dumps(
        {
            "schema_version": "1.0",
            "frame_index": 1,
            "occurred_at": datetime.now(UTC).isoformat(),
            "width": 1,
            "height": 1,
            "correlation_id": "smoke-correlation",
        },
        separators=(",", ":"),
    ).encode()
    packet = struct.pack(">I", len(metadata)) + metadata + b"\xff\xd8\xff\xd9"
    view = "smoke_input"
    with (
        connect(f"{WS_URL}/ws/v1/trips/T01-Sample/camera/{view}") as viewer,
        connect(f"{WS_URL}/ws/v1/trips/T01-Sample/camera/{view}?role=producer") as producer,
    ):
        producer.send(packet)
        response = json.loads(producer.recv(timeout=5))
        received = viewer.recv(timeout=5)
    if response["status"] != "accepted" or response["frame_index"] != 1:
        raise RuntimeError("camera WebSocket failed")
    if received != packet:
        raise RuntimeError("camera viewer did not receive the producer frame")


def historical_replay() -> None:
    with connect(f"{WS_URL}/ws/v1/trips/T01-Sample/camera/road_left") as viewer:
        frames = [_packet_frame_index(viewer.recv(timeout=5)) for _ in range(3)]
    if frames != sorted(frames) or len(set(frames)) != len(frames):
        raise RuntimeError(f"historical camera replay was not strictly ordered: {frames}")


def trip_trajectory() -> None:
    fleet_status, fleet_payload = http_json(f"{API_URL}/api/v1/trips")
    status, payload = http_json(f"{API_URL}/api/v1/trips/T01-Sample/trajectory")
    try:
        summaries = fleet_payload["data"]["items"]
        summary = next(item for item in summaries if item["trip_id"] == "T01-Sample")
        points = payload["data"]["points"]
        first = points[0]
    except (IndexError, KeyError, StopIteration, TypeError) as error:
        raise RuntimeError("fleet or trajectory payload was incomplete") from error
    if fleet_status != 200 or not isinstance(summary.get("safety_score"), int):
        raise RuntimeError("fleet summary did not expose the documented aggregate score")
    if status != 200 or len(points) != 600:
        raise RuntimeError("trajectory did not include all organizer telemetry frames")
    required = {"frame_index", "speed_kmh", "driver_state", "active_event_types"}
    if not required.issubset(first):
        raise RuntimeError("trajectory did not expose frame-synchronised telemetry")


def _packet_frame_index(packet: object) -> int:
    if not isinstance(packet, bytes) or len(packet) < 4:
        raise RuntimeError("historical replay packet was not binary")
    metadata_length = struct.unpack(">I", packet[:4])[0]
    try:
        metadata = json.loads(packet[4 : 4 + metadata_length])
        return int(metadata["frame_index"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("historical replay metadata was invalid") from error


def carsky_acknowledgement() -> None:
    command_id = str(uuid4())
    command = {
        "schema_version": "1.0",
        "command_id": command_id,
        "event_id": str(uuid4()),
        "correlation_id": "smoke-correlation",
        "vehicle_id": "vehicle-1",
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(seconds=30)).isoformat(),
        "channel": "visual",
        "priority": 5,
        "title": "Collision risk",
        "message": "Brake now. Increase distance.",
        "dedupe_key": f"smoke.{command_id}",
    }
    status, _ = http_json(f"{BRIDGE_URL}/v1/coaching", payload=command)
    ack_status, acknowledgement = http_json(
        f"{BRIDGE_URL}/v1/coaching/{command_id}/ack",
        payload={},
    )
    if status != 202 or ack_status != 200 or not acknowledgement["acknowledged"]:
        raise RuntimeError("CarSky acknowledgement failed")


def main() -> None:
    wait_ready()
    print("1/8 API readiness: ok")
    mqtt_round_trip()
    print("2/8 telemetry publish: ok")
    model_inference()
    print("3/8 local inference: ok")
    print("4/8 risk event receive: ok")
    camera_websocket()
    print("5/8 producer camera WebSocket: ok")
    historical_replay()
    print("6/8 historical camera replay: ok")
    trip_trajectory()
    print("7/8 fleet and trajectory telemetry: ok")
    carsky_acknowledgement()
    print("8/8 mock CarSky acknowledgement: ok")


if __name__ == "__main__":
    main()
