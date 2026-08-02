"""Stream organizer road-camera JPEG frames into the FleetIQ camera WebSocket."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image
from websockets.sync.client import connect


VIEW_DIRECTORIES = {
    "road_left": "image_2",
    "road_right": "image_3",
}


def build_camera_packet(
    *,
    jpeg: bytes,
    frame_index: int,
    width: int,
    height: int,
    occurred_at: datetime,
    correlation_id: str,
) -> bytes:
    metadata = json.dumps(
        {
            "schema_version": "1.0",
            "frame_index": frame_index,
            "occurred_at": occurred_at.isoformat(),
            "width": width,
            "height": height,
            "correlation_id": correlation_id,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return len(metadata).to_bytes(4, "big", signed=False) + metadata + jpeg


def resolve_view_directory(dataset_root: Path, trip: str, view: str) -> Path:
    try:
        directory_name = VIEW_DIRECTORIES[view]
    except KeyError as error:
        raise ValueError(f"unsupported camera view: {view}") from error
    directory = dataset_root / trip / "kitti" / directory_name
    if not directory.is_dir():
        raise FileNotFoundError(f"camera directory not found: {directory}")
    return directory


def frame_paths(directory: Path, *, start: int, max_frames: int | None) -> list[Path]:
    frames = sorted(path for path in directory.glob("*.jpg") if path.stem.isdigit())
    selected = [path for path in frames if int(path.stem) >= start]
    if max_frames is not None:
        selected = selected[:max_frames]
    if not selected:
        raise FileNotFoundError(f"no JPEG frames found in {directory}")
    return selected


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def stream_frames(
    *,
    dataset_root: Path,
    trip: str,
    view: str,
    ws_base_url: str,
    fps: float,
    start: int,
    max_frames: int | None,
) -> int:
    if fps <= 0:
        raise ValueError("fps must be positive")
    directory = resolve_view_directory(dataset_root, trip, view)
    frames = frame_paths(directory, start=start, max_frames=max_frames)
    interval_s = 1.0 / fps
    url = f"{ws_base_url.rstrip('/')}/ws/v1/trips/{trip}/camera/{view}?role=producer"
    sent = 0
    with connect(url) as socket:
        for path in frames:
            frame_index = int(path.stem)
            jpeg = path.read_bytes()
            width, height = image_size(path)
            packet = build_camera_packet(
                jpeg=jpeg,
                frame_index=frame_index,
                width=width,
                height=height,
                occurred_at=datetime.now(UTC),
                correlation_id=f"{trip}.{view}.{frame_index:06d}",
            )
            socket.send(packet)
            acknowledgement = json.loads(socket.recv(timeout=5))
            if acknowledgement.get("status") != "accepted":
                raise RuntimeError(f"camera frame was not accepted: {acknowledgement}")
            sent += 1
            time.sleep(interval_s)
    return sent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("data/Practice_Dataset/Practice_Dataset"),
    )
    parser.add_argument("--trip", default="T01-Sample")
    parser.add_argument("--view", choices=tuple(VIEW_DIRECTORIES), default="road_left")
    parser.add_argument("--ws-base-url", default="ws://localhost:8000")
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--max-frames", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sent = stream_frames(
        dataset_root=args.dataset_root,
        trip=args.trip,
        view=args.view,
        ws_base_url=args.ws_base_url,
        fps=args.fps,
        start=args.start,
        max_frames=args.max_frames,
    )
    print(f"{args.trip}/{args.view}: streamed {sent} frame(s)")


if __name__ == "__main__":
    main()
