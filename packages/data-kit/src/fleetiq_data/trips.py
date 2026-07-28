"""Trip discovery, gzip document loading, and a small local-data CLI."""

from __future__ import annotations

import argparse
import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fleetiq_data.paths import DatasetPaths


@dataclass(frozen=True, slots=True)
class TripRecord:
    """A trip folder and its unchanged organizer directory layout."""

    dataset_root: Path
    trip_id: str

    @property
    def trip_dir(self) -> Path:
        return self.dataset_root / self.trip_id

    @property
    def document_path(self) -> Path:
        return self.trip_dir / f"{self.trip_id}.json.gz"

    @property
    def driver_dir(self) -> Path:
        return self.trip_dir / "driver"

    @property
    def kitti_dir(self) -> Path:
        return self.trip_dir / "kitti"

    @property
    def image_2_dir(self) -> Path:
        return self.kitti_dir / "image_2"

    @property
    def image_3_dir(self) -> Path:
        return self.kitti_dir / "image_3"

    @property
    def depth_dir(self) -> Path:
        return self.kitti_dir / "depth"

    @property
    def calib_dir(self) -> Path:
        return self.kitti_dir / "calib"

    def label_dir(self, name: str = "label_2") -> Path:
        return self.kitti_dir / name


def discover_trips(root: Path | DatasetPaths) -> list[TripRecord]:
    """Discover valid trip folders directly below an explicit dataset root."""
    dataset_root = _root_path(root)
    if not dataset_root.is_dir():
        return []
    return [
        TripRecord(dataset_root=dataset_root, trip_id=path.name)
        for path in sorted(dataset_root.iterdir())
        if path.is_dir() and (path / f"{path.name}.json.gz").is_file()
    ]


def resolve_trip(root: Path | DatasetPaths, trip_id: str) -> TripRecord:
    """Resolve one trip ID case-insensitively under an explicit dataset root."""
    for record in discover_trips(root):
        if record.trip_id.casefold() == trip_id.casefold():
            return record
    raise FileNotFoundError(f"Trip '{trip_id}' was not found under {_root_path(root)}")


def load_trip_document(trip: TripRecord | Path) -> dict[str, Any]:
    """Load a trip's organizer gzip JSON document without reshaping it."""
    document_path = trip.document_path if isinstance(trip, TripRecord) else _document_path(trip)
    with gzip.open(document_path, "rt", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise TypeError(f"Trip document must contain a JSON object: {document_path}")
    return document


def _root_path(root: Path | DatasetPaths) -> Path:
    return root.root if isinstance(root, DatasetPaths) else Path(root)


def _document_path(trip_dir: Path) -> Path:
    trip_dir = Path(trip_dir)
    return trip_dir / f"{trip_dir.name}.json.gz"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List FleetIQ organizer trip identifiers.")
    parser.add_argument("--root", type=Path, required=True, help="Dataset root containing trip folders.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.root.is_dir():
        print(f"Dataset root does not exist: {args.root}")
        return 2
    for trip in discover_trips(args.root):
        print(trip.trip_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
