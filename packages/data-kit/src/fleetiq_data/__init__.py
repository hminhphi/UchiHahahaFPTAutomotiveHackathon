"""Stable, explicit-root access to FleetIQ organizer datasets."""

from typing import TYPE_CHECKING

from fleetiq_data.calibration import Calibration, parse_calibration
from fleetiq_data.kitti import KittiObject, find_frame, parse_kitti_labels
from fleetiq_data.paths import DatasetPaths

if TYPE_CHECKING:
    from fleetiq_data.trips import TripRecord

__all__ = [
    "Calibration",
    "DatasetPaths",
    "KittiObject",
    "TripRecord",
    "discover_trips",
    "find_frame",
    "load_trip_document",
    "parse_calibration",
    "parse_kitti_labels",
    "resolve_trip",
]


def __getattr__(name: str) -> object:
    """Defer trip imports so ``python -m fleetiq_data.trips`` stays warning-free."""
    if name in {"TripRecord", "discover_trips", "load_trip_document", "resolve_trip"}:
        from fleetiq_data.trips import (
            TripRecord,
            discover_trips,
            load_trip_document,
            resolve_trip,
        )

        return {
            "TripRecord": TripRecord,
            "discover_trips": discover_trips,
            "load_trip_document": load_trip_document,
            "resolve_trip": resolve_trip,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
