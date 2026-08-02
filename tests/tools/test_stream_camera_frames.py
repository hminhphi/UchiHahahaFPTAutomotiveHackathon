import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.visualization.stream_camera_frames import (
    build_camera_packet,
    frame_paths,
    image_size,
    resolve_view_directory,
)


def test_build_camera_packet_uses_protocol_metadata_prefix() -> None:
    packet = build_camera_packet(
        jpeg=b"\xff\xd8frame\xff\xd9",
        frame_index=7,
        width=640,
        height=360,
        occurred_at=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
        correlation_id="corr-7",
    )

    metadata_length = int.from_bytes(packet[:4], "big")
    metadata = json.loads(packet[4 : 4 + metadata_length])

    assert metadata == {
        "schema_version": "1.0",
        "frame_index": 7,
        "occurred_at": "2026-07-31T12:00:00+00:00",
        "width": 640,
        "height": 360,
        "correlation_id": "corr-7",
    }
    assert packet[4 + metadata_length :] == b"\xff\xd8frame\xff\xd9"


def test_resolve_view_directory_maps_camera_views(tmp_path: Path) -> None:
    dataset_root = tmp_path / "Practice_Dataset"
    image_2 = dataset_root / "T01-Sample" / "kitti" / "image_2"
    image_3 = dataset_root / "T01-Sample" / "kitti" / "image_3"
    image_2.mkdir(parents=True)
    image_3.mkdir(parents=True)

    assert resolve_view_directory(dataset_root, "T01-Sample", "road_left") == image_2
    assert resolve_view_directory(dataset_root, "T01-Sample", "road_right") == image_3


def test_frame_paths_limits_sorted_jpegs(tmp_path: Path) -> None:
    for name in ("000002.jpg", "000000.jpg", "000001.jpg", "note.txt"):
        (tmp_path / name).write_bytes(b"data")

    assert [path.name for path in frame_paths(tmp_path, start=1, max_frames=2)] == [
        "000001.jpg",
        "000002.jpg",
    ]


def test_image_size_reads_jpeg_dimensions(tmp_path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow is not installed")

    path = tmp_path / "frame.jpg"
    Image.new("RGB", (8, 6)).save(path, format="JPEG")

    assert image_size(path) == (8, 6)
