"""Lightweight dataset-root resolution for offline road-facing commands."""

from __future__ import annotations

from pathlib import Path

from fleetiq_data import DatasetPaths, discover_trips as discover_trip_records
from fleetiq_data import resolve_trip as resolve_trip_record


PROJECT_ROOT = Path(__file__).resolve().parents[5]
PRACTICE_ROOT = (
    PROJECT_ROOT / "data" / "Practice_Dataset" / "Practice_Dataset"
).resolve()
REDACTED_ROOT = (
    PROJECT_ROOT
    / "data"
    / "Hackathon_Dataset_Redacted"
    / "Hackathon_Dataset_Redacted"
).resolve()


def environment_dataset_root() -> Path | None:
    """Return the configured organizer root without consulting the cwd."""
    try:
        return DatasetPaths.from_env().root.resolve()
    except ValueError:
        return None


def dataset_roots(dataset: str | Path = "all") -> tuple[Path, ...]:
    """Map a named organizer dataset or explicit root to concrete roots."""
    if isinstance(dataset, Path):
        return (dataset.expanduser().resolve(),)
    if dataset not in {"practice", "redacted", "all"}:
        return (Path(dataset).expanduser().resolve(),)

    configured_root = environment_dataset_root()
    if configured_root is not None:
        return (configured_root,)
    if dataset == "practice":
        return (PRACTICE_ROOT,)
    if dataset == "redacted":
        return (REDACTED_ROOT,)
    if dataset == "all":
        return (PRACTICE_ROOT, REDACTED_ROOT)
    raise AssertionError(f"Unhandled dataset selector: {dataset}")


def discover_trip_dirs(dataset: str | Path = "all") -> list[Path]:
    """Return organizer trip directories while preserving the old CLI shape."""
    return [
        record.trip_dir
        for root in dataset_roots(dataset)
        for record in discover_trip_records(DatasetPaths(root))
    ]


def resolve_trip_dir(trip_id: str, dataset: str | Path = "all") -> Path:
    """Resolve one trip across the selected explicit dataset roots."""
    for root in dataset_roots(dataset):
        try:
            return resolve_trip_record(DatasetPaths(root), trip_id).trip_dir
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"Trip not found: {trip_id}")
