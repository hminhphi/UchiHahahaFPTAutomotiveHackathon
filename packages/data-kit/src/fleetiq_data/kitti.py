"""Organizer-preserving KITTI labels and frame path lookup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class KittiObject:
    """One standard KITTI object-label row."""

    object_type: str
    truncated: float
    occluded: int
    alpha: float
    bbox: tuple[float, float, float, float]
    dimensions: tuple[float, float, float]
    location: tuple[float, float, float]
    rotation_y: float
    score: float | None = None


def parse_kitti_labels(path: Path) -> list[KittiObject]:
    """Read standard KITTI labels, ignoring incomplete organizer rows."""
    path = Path(path)
    if not path.is_file():
        return []

    objects: list[KittiObject] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) < 15:
            continue
        try:
            values = [float(value) for value in fields[1:]]
        except ValueError:
            continue
        objects.append(
            KittiObject(
                object_type=fields[0],
                truncated=values[0],
                occluded=int(values[1]),
                alpha=values[2],
                bbox=tuple(values[3:7]),  # type: ignore[arg-type]
                dimensions=tuple(values[7:10]),  # type: ignore[arg-type]
                location=tuple(values[10:13]),  # type: ignore[arg-type]
                rotation_y=values[13],
                score=values[14] if len(values) > 14 else None,
            )
        )
    return objects


def find_frame(
    directory: Path,
    frame_id: int,
    *,
    suffixes: tuple[str, ...] = (".jpg", ".png", ".jpeg"),
    policy: Literal["exact", "previous", "nearest"] = "exact",
) -> Path | None:
    """Find an image or sparse depth frame under an organizer directory."""
    directory = Path(directory)
    if not directory.is_dir():
        return None
    if policy not in {"exact", "previous", "nearest"}:
        raise ValueError(f"Unsupported frame policy: {policy}")

    candidates = _numbered_frames(directory, suffixes)
    if policy == "exact":
        return candidates.get(frame_id)
    if not candidates:
        return None
    available = sorted(candidates)
    if policy == "previous":
        prior = [value for value in available if value <= frame_id]
        selected = prior[-1] if prior else available[0]
    else:
        selected = min(available, key=lambda value: (abs(value - frame_id), value))
    return candidates[selected]


def _numbered_frames(directory: Path, suffixes: tuple[str, ...]) -> dict[int, Path]:
    allowed = {suffix.lower() for suffix in suffixes}
    frames: dict[int, Path] = {}
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in allowed and path.stem.isdigit():
            frames.setdefault(int(path.stem), path)
    return frames
