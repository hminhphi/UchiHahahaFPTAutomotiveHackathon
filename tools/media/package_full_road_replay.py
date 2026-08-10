"""Package complete road-left replay video and frame map for every redacted trip."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def discover_trip_dirs(dataset_root: Path) -> list[Path]:
    return sorted(
        trip_dir
        for trip_dir in dataset_root.iterdir()
        if trip_dir.is_dir() and trip_dir.name.startswith("T") and trip_dir.name.endswith("d")
    )


def load_frame_ids(trip_dir: Path) -> list[int]:
    document = json.loads(gzip.decompress((trip_dir / f"{trip_dir.name}.json.gz").read_bytes()))
    frames = document.get("frames", [])
    return [int(frame.get("frame_id", index)) for index, frame in enumerate(frames)]


def write_missing_frame(path: Path, width: int = 640, height: int = 360) -> None:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(image, "SOURCE FRAME UNAVAILABLE", (100, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 220, 255), 2)
    cv2.putText(image, path.stem, (250, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 220, 255), 1)
    # Preserve the source frames' 4:4:4 JPEG sampling so FFmpeg never drops a
    # frame while its concat decoder changes pixel format at an unavailable slot.
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb_image).save(path, "JPEG", quality=95, subsampling=0)


def quote_concat_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", r"'\''")


def valid_source_image(path: Path) -> bool:
    """Require an image that can be decoded, not merely a directory entry."""
    return path.is_file() and cv2.imread(str(path), cv2.IMREAD_COLOR) is not None


def package_trip(trip_dir: Path, artifacts_root: Path, fps: float, ffmpeg: str) -> tuple[int, list[int]]:
    frame_ids = load_frame_ids(trip_dir)
    media_dir = artifacts_root / trip_dir.name / "media" / "road_left"
    media_dir.mkdir(parents=True, exist_ok=True)
    image_dir = trip_dir / "kitti" / "image_2"
    # The concat demuxer requires the marker to use the same JPEG codec as source frames.
    missing_marker = media_dir / "missing_source_frame.jpg"
    source_paths = {
        frame_id: image_dir / f"{frame_id:06d}.jpg"
        for frame_id in frame_ids
    }
    missing_frames = [frame_id for frame_id, path in source_paths.items() if not valid_source_image(path)]
    if missing_frames:
        write_missing_frame(missing_marker)
    last_source = source_paths[frame_ids[-1]]
    if frame_ids[-1] in missing_frames:
        last_source = missing_marker

    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as handle:
        concat_path = Path(handle.name)
        for frame_id in frame_ids:
            source = source_paths[frame_id]
            if frame_id in missing_frames:
                source = missing_marker
            handle.write(f"file '{quote_concat_path(source)}'\n")
            handle.write(f"duration {1 / fps:.9f}\n")
        handle.write(f"file '{quote_concat_path(last_source)}'\n")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_path),
                "-vf", f"fps={fps}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(media_dir / "source.mp4"),
            ],
            check=True,
        )
    finally:
        concat_path.unlink(missing_ok=True)

    manifest = {
        "fps": fps,
        "entries": [
            {"frame_index": frame_id, "time_s": frame_id / fps, "source_available": frame_id not in missing_frames}
            for frame_id in frame_ids
        ],
    }
    (media_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return len(frame_ids), missing_frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, default=Path("artifacts/trips"))
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    args = parser.parse_args()

    if not args.dataset_root.is_dir():
        raise SystemExit(f"Dataset root not found: {args.dataset_root}")
    if args.fps <= 0:
        raise SystemExit("FPS must be positive")
    if not args.ffmpeg:
        raise SystemExit("ffmpeg is required to package full road replay")

    trip_dirs = discover_trip_dirs(args.dataset_root)
    if not trip_dirs:
        raise SystemExit("No redacted trips found")
    for trip_dir in trip_dirs:
        frame_count, missing_frames = package_trip(trip_dir, args.artifacts_root, args.fps, args.ffmpeg)
        suffix = f"; source gaps: {missing_frames}" if missing_frames else ""
        print(f"{trip_dir.name}: packaged {frame_count} road frames{suffix}")


if __name__ == "__main__":
    main()
