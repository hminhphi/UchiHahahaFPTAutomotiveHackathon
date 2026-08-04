"""Build safe, dashboard-ready trip trajectories from organizer telemetry."""

from __future__ import annotations

import math
from typing import Any

from .schemas import TrajectoryData, TrajectoryPoint

_MAX_PLAUSIBLE_ACCEL_MPS2 = 12.0
_HARSH_BRAKE_MPS2 = -4.0
_FAST_CORNER_MPS2 = 3.0


def build_trajectory(trip_id: str, document: dict[str, Any]) -> TrajectoryData:
    """Use CARLA world positions for geometry and acceleration for event context.

    Integrating acceleration would accumulate drift even for small telemetry errors.
    The provided ``ego.location`` is the authoritative simulator position, so it
    determines each segment while filtered acceleration marks the safety context.
    """
    raw_frames = document.get("frames")
    if not isinstance(raw_frames, list):
        return TrajectoryData(
            trip_id=trip_id,
            distance_m=0,
            max_speed_kmh=0,
            max_lateral_accel_mps2=0,
        )

    points: list[TrajectoryPoint] = []
    distance_m = 0.0
    max_speed_kmh = 0.0
    max_lateral_accel_mps2 = 0.0
    previous: TrajectoryPoint | None = None
    for fallback_index, raw_frame in enumerate(raw_frames):
        if not isinstance(raw_frame, dict):
            continue
        ego = raw_frame.get("ego")
        if not isinstance(ego, dict):
            continue
        location = ego.get("location")
        if not isinstance(location, dict):
            continue
        x_m = _finite(location.get("x"))
        y_m = _finite(location.get("y"))
        if x_m is None or y_m is None:
            continue
        speed_kmh = max(0.0, _finite(ego.get("speed_kmh")) or 0.0)
        long_accel = _bounded_accel(ego.get("longitudinal_accel"))
        lat_accel = _bounded_accel(ego.get("lateral_accel"))
        flags = raw_frame.get("behavior_flags")
        events = _events(flags, long_accel, lat_accel)
        driver = raw_frame.get("driver")
        risk = raw_frame.get("risk")
        point = TrajectoryPoint(
            frame_index=_int(raw_frame.get("frame_id"), fallback_index),
            timestamp_s=max(0.0, _finite(raw_frame.get("timestamp")) or fallback_index / 20.0),
            x_m=x_m,
            y_m=y_m,
            speed_kmh=min(speed_kmh, 300.0),
            longitudinal_accel_mps2=long_accel,
            lateral_accel_mps2=lat_accel,
            min_ttc_s=_finite_nonnegative(raw_frame.get("min_ttc")),
            headway_s=_finite_nonnegative(raw_frame.get("headway_sec")),
            driver_state=_string_field(driver, "state", "unknown"),
            phone_use=_optional_bool(_mapping_value(driver, "phone_use")),
            driver_alertness=_bounded_unit(_mapping_value(driver, "alertness_score")),
            simulator_risk_score=_bounded_score(_mapping_value(risk, "final_risk_score")),
            active_event_types=_active_event_types(raw_frame.get("events_active")),
            events=events,
        )
        if previous is not None:
            distance_m += math.hypot(point.x_m - previous.x_m, point.y_m - previous.y_m)
        previous = point
        points.append(point)
        max_speed_kmh = max(max_speed_kmh, point.speed_kmh)
        max_lateral_accel_mps2 = max(max_lateral_accel_mps2, abs(point.lateral_accel_mps2))

    return TrajectoryData(
        trip_id=trip_id,
        points=tuple(points),
        distance_m=round(distance_m, 2),
        max_speed_kmh=round(max_speed_kmh, 1),
        max_lateral_accel_mps2=round(max_lateral_accel_mps2, 2),
    )


def _events(flags: object, long_accel: float, lat_accel: float) -> tuple[str, ...]:
    values = flags if isinstance(flags, dict) else {}
    events = []
    if values.get("harsh_brake") is True or long_accel <= _HARSH_BRAKE_MPS2:
        events.append("harsh_brake")
    if values.get("harsh_corner") is True or abs(lat_accel) >= _FAST_CORNER_MPS2:
        events.append("fast_corner")
    if values.get("speeding") is True:
        events.append("speeding")
    return tuple(events)


def _bounded_accel(value: object) -> float:
    finite = _finite(value) or 0.0
    return max(-_MAX_PLAUSIBLE_ACCEL_MPS2, min(_MAX_PLAUSIBLE_ACCEL_MPS2, finite))


def _finite(value: object) -> float | None:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    return candidate if math.isfinite(candidate) else None


def _finite_nonnegative(value: object) -> float | None:
    candidate = _finite(value)
    return candidate if candidate is not None and candidate >= 0 else None


def _mapping_value(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, dict) else None


def _string_field(value: object, key: str, fallback: str) -> str:
    candidate = _mapping_value(value, key)
    return candidate.strip().lower() if isinstance(candidate, str) and candidate.strip() else fallback


def _bounded_unit(value: object) -> float | None:
    candidate = _finite(value)
    return max(0.0, min(1.0, candidate)) if candidate is not None else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _bounded_score(value: object) -> float | None:
    candidate = _finite(value)
    return max(0.0, min(100.0, candidate)) if candidate is not None else None


def _active_event_types(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    event_types = []
    for event in value:
        if not isinstance(event, dict):
            continue
        event_type = event.get("event_type")
        if isinstance(event_type, str) and event_type.strip():
            event_types.append(event_type.strip())
    return tuple(event_types)


def _int(value: object, fallback: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return fallback
