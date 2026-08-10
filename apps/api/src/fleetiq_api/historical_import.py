"""Idempotently seed organizer trips into FleetIQ operational records."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from .dependencies import OperationsRepository
from .historical_replay import TripMediaStore
from .operations import DeliveryOrderRecord, DriverRecord, EventMarker, LiveTelemetryInput, TripDetail, VehicleRecord
from .trajectory import build_trajectory


@dataclass(frozen=True)
class HistoricalImportResult:
    trip_id: str
    status: str
    telemetry_samples: int


class HistoricalTripImporter:
    def __init__(
        self,
        media: TripMediaStore,
        repository: OperationsRepository,
        profiles: dict[str, dict[str, object]],
        *,
        seed_version: str,
    ) -> None:
        self._media = media
        self._repository = repository
        self._profiles = profiles
        self._seed_version = seed_version

    async def import_trip(self, trip_id: str) -> HistoricalImportResult:
        profile = self._profiles.get(trip_id)
        if profile is None:
            raise KeyError(f"no logistics profile for {trip_id}")
        existing = await self._repository.get_trip(trip_id)
        if (
            existing is not None
            and existing.source == "historical"
            and existing.organizer_trip_id == trip_id
            and existing.seed_version == self._seed_version
        ):
            return HistoricalImportResult(trip_id=trip_id, status="unchanged", telemetry_samples=0)

        trip = _trip(trip_id, profile, self._seed_version)
        document = await self._media.read_trip_document(trip_id)
        telemetry_samples = _telemetry(document)

        await self._repository.upsert_vehicle(_vehicle(profile))
        await self._repository.upsert_driver(_driver(profile))
        # The seed version is the completion marker; never mark a partial import unchanged.
        await self._repository.upsert_trip(trip.model_copy(update={"seed_version": None}))
        for order in _orders(trip):
            await self._repository.upsert_order(order)

        sample_count = 0
        for telemetry in telemetry_samples:
            await self._repository.upsert_live_telemetry(trip_id, telemetry)
            sample_count += 1
        await self._import_events(trip_id, document)
        await self._repository.upsert_trip(trip)
        return HistoricalImportResult(trip_id=trip_id, status="imported", telemetry_samples=sample_count)

    async def _import_events(self, trip_id: str, document: dict[str, object]) -> None:
        selected: dict[str, EventMarker] = {}
        for point in build_trajectory(trip_id, document).points:
            for raw_type in (*point.events, *point.active_event_types):
                event_type = raw_type.strip().lower().replace(" ", "_").replace("-", "_")
                if not event_type or event_type in selected:
                    continue
                severity, title = _event_presentation(event_type)
                try:
                    selected[event_type] = EventMarker(
                        event_id=f"{trip_id}.{event_type}.{point.frame_index}",
                        trip_id=trip_id,
                        frame_index=point.frame_index,
                        severity=severity,
                        event_type=event_type,
                        title=title,
                        confidence=0.9,
                    )
                except ValueError:
                    continue
        for event in selected.values():
            await self._repository.upsert_event(event)

    async def import_all(self) -> tuple[HistoricalImportResult, ...]:
        trip_ids = await self._media.list_trip_ids()
        results = []
        for trip_id in sorted(trip_ids):
            if trip_id in self._profiles:
                results.append(await self.import_trip(trip_id))
        return tuple(results)


def load_logistics_seed(path: object) -> tuple[str, dict[str, dict[str, object]]]:
    from pathlib import Path
    payload = json.loads(Path(str(path)).read_text(encoding="utf-8"))
    version = payload.get("seed_version")
    profiles = payload.get("profiles")
    if not isinstance(version, str) or not version or not isinstance(profiles, dict):
        raise ValueError("logistics seed must contain seed_version and profiles")
    normalized = {
        trip_id: profile
        for trip_id, profile in profiles.items()
        if isinstance(trip_id, str) and isinstance(profile, dict)
    }
    if len(normalized) != len(profiles):
        raise ValueError("logistics profiles must be keyed by trip identifier")
    return version, normalized


def _vehicle(profile: dict[str, object]) -> VehicleRecord:
    return VehicleRecord(
        vehicle_id=_text(profile, "vehicle_id"),
        vehicle_class=_text(profile, "vehicle_class"),
        license_plate=_text(profile, "license_plate"),
        length_m=_number(profile, "length_m"),
        width_m=_number(profile, "width_m"),
        height_m=_number(profile, "height_m"),
        payload_capacity_kg=_number(profile, "payload_capacity_kg"),
        depot_name=_text(profile, "depot_name"),
    )


def _driver(profile: dict[str, object]) -> DriverRecord:
    return DriverRecord(
        driver_id=_text(profile, "driver_id"),
        display_name=_text(profile, "driver_name"),
        employee_code=_text(profile, "employee_code"),
        license_class=_text(profile, "license_class"),
        home_depot=_text(profile, "depot_name"),
    )


def _trip(trip_id: str, profile: dict[str, object], seed_version: str) -> TripDetail:
    return TripDetail(
        trip_id=trip_id,
        vehicle_id=_text(profile, "vehicle_id"),
        driver_id=_text(profile, "driver_id"),
        source="historical",
        status="complete",
        organizer_trip_id=trip_id,
        seed_version=seed_version,
        route_name=_text(profile, "route_name"),
        cargo_class=_text(profile, "cargo_class"),
        vehicle_class=_text(profile, "vehicle_class"),
        order_count=_integer(profile, "order_count"),
    )


def _orders(trip: TripDetail) -> tuple[DeliveryOrderRecord, ...]:
    return tuple(
        DeliveryOrderRecord(
            order_id=f"{trip.trip_id}-ORD-{index:03d}",
            trip_id=trip.trip_id,
            status="delivered",
            cargo_class=trip.cargo_class,
            package_count=1,
            destination=trip.route_name,
        )
        for index in range(1, trip.order_count + 1)
    )


def _event_presentation(event_type: str) -> tuple[int, str]:
    presentations = {
        "short_ttc": (4, "Short TTC detected"),
        "near_miss": (5, "Near-miss risk detected"),
        "harsh_brake": (4, "Harsh braking detected"),
        "fast_corner": (3, "Fast corner detected"),
        "speeding": (3, "Speeding telemetry flag"),
        "drowsiness": (4, "Driver drowsiness detected"),
        "distraction": (3, "Driver distraction detected"),
    }
    return presentations.get(event_type, (3, event_type.replace("_", " ").title()))


def _telemetry(document: dict[str, object]) -> tuple[LiveTelemetryInput, ...]:
    frames = document.get("frames")
    if not isinstance(frames, list):
        return ()
    values: list[LiveTelemetryInput] = []
    for raw_frame in frames:
        if not isinstance(raw_frame, dict) or not isinstance(raw_frame.get("ego"), dict):
            continue
        ego = raw_frame["ego"]
        frame_index = _finite_int(raw_frame.get("frame_id"))
        timestamp_s = _finite_number(raw_frame.get("timestamp"))
        speed_kmh = _finite_number(ego.get("speed_kmh"))
        if frame_index is None or timestamp_s is None or speed_kmh is None:
            continue
        values.append(
            LiveTelemetryInput(
                frame_index=frame_index,
                timestamp_s=timestamp_s,
                speed_kmh=speed_kmh,
                longitudinal_accel_mps2=_finite_any_number(ego.get("longitudinal_accel")),
                lateral_accel_mps2=_finite_any_number(ego.get("lateral_accel")),
            )
        )
    return tuple(values)


def _text(value: dict[str, object], key: str) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"profile field {key} must be non-empty text")
    return candidate


def _number(value: dict[str, object], key: str) -> float:
    candidate = _finite_number(value.get(key))
    if candidate is None:
        raise ValueError(f"profile field {key} must be finite")
    return candidate


def _integer(value: dict[str, object], key: str) -> int:
    candidate = _finite_int(value.get(key))
    if candidate is None:
        raise ValueError(f"profile field {key} must be a non-negative integer")
    return candidate


def _finite_number(value: object) -> float | None:
    candidate = _finite_any_number(value)
    return candidate if candidate is not None and candidate >= 0 else None


def _finite_any_number(value: object) -> float | None:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    return candidate if math.isfinite(candidate) else None


def _finite_int(value: object) -> int | None:
    candidate = _finite_number(value)
    return int(candidate) if candidate is not None and candidate.is_integer() else None
