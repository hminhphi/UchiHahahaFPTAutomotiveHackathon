import json
from datetime import UTC, datetime

import pytest
from fleetiq_api.ws.frame_protocol import (
    FrameProtocolError,
    decode_camera_frame,
)


def _packet(metadata: dict[str, object], jpeg: bytes = b"\xff\xd8frame\xff\xd9") -> bytes:
    encoded = json.dumps(metadata).encode("utf-8")
    return len(encoded).to_bytes(4, "big") + encoded + jpeg


def _metadata() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "frame_index": 7,
        "occurred_at": datetime(2026, 7, 29, 12, 0, tzinfo=UTC).isoformat(),
        "width": 640,
        "height": 360,
        "correlation_id": "corr-7",
    }


def test_decode_camera_frame_uses_big_endian_metadata_length() -> None:
    frame = decode_camera_frame(_packet(_metadata()), max_metadata_bytes=1024, max_frame_bytes=1024)

    assert frame.metadata.frame_index == 7
    assert frame.metadata.width == 640
    assert frame.jpeg == b"\xff\xd8frame\xff\xd9"


@pytest.mark.parametrize(
    ("packet", "code"),
    [
        ((1025).to_bytes(4, "big") + b"{}", 1009),
        (b"\x00\x00\x00\x10{}", 1007),
        (b"\x00\x00\x00\x02\xff\xff\xff\xd8x\xff\xd9", 1007),
        (_packet({"schema_version": "1.0"}), 1007),
        (_packet(_metadata(), b"not-jpeg"), 1003),
    ],
)
def test_decode_camera_frame_rejects_malformed_payloads(packet: bytes, code: int) -> None:
    with pytest.raises(FrameProtocolError) as error:
        decode_camera_frame(packet, max_metadata_bytes=1024, max_frame_bytes=1024)

    assert error.value.close_code == code


def test_decode_camera_frame_rejects_oversized_jpeg() -> None:
    with pytest.raises(FrameProtocolError) as error:
        decode_camera_frame(_packet(_metadata(), b"\xff\xd8too-large\xff\xd9"), 1024, 4)

    assert error.value.close_code == 1009
