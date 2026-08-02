"""Build transparent aggregate trip summaries for the fleet dashboard."""

from __future__ import annotations

import math
from typing import Any

from .schemas import TripSummary


def build_trip_summary(trip_id: str, document: dict[str, Any]) -> TripSummary:
    """Score documented organizer telemetry without presenting it as model output."""
    aggregate = _mapping(document.get("trip_aggregate"))
    driver_summary = _mapping(document.get("driver_summary"))
    near_miss_count = _nonnegative_int(aggregate.get("near_miss_count"))
    harsh_brake_count = _nonnegative_int(aggregate.get("harsh_brake_count"))
    harsh_corner_count = _nonnegative_int(aggregate.get("harsh_corner_count"))
    speeding_pct = _finite(aggregate.get("speeding_pct_time")) or 0.0
    alertness = _unit(driver_summary.get("average_alertness_score"))
    penalty = (
        min(35, near_miss_count * 3)
        + min(15, harsh_brake_count)
        + min(10, harsh_corner_count * 2)
        + min(15, round(max(0.0, speeding_pct) * 0.2))
        + round((1 - alertness) * 20)
    )
    score = max(0, 100 - penalty)
    max_risk = _finite(aggregate.get("max_risk_score")) or 0.0
    severity = _severity(score, max_risk)
    return TripSummary(
        trip_id=trip_id,
        status="available",
        safety_score=score,
        severity=severity,
        latest_alert=_latest_alert(near_miss_count, harsh_brake_count, harsh_corner_count, speeding_pct),
        driver_state=_dominant_driver_state(driver_summary),
        max_speed_kmh=_max_speed(document.get("frames")),
    )


def _severity(score: int, max_risk: float) -> int:
    if max_risk >= 80 or score <= 45:
        return 5
    if max_risk >= 60 or score <= 60:
        return 4
    if max_risk >= 30 or score <= 75:
        return 3
    if score <= 90:
        return 2
    return 1


def _latest_alert(near_miss: int, harsh_brake: int, harsh_corner: int, speeding_pct: float) -> str:
    if near_miss:
        return f"{near_miss} near-miss event(s) in organizer telemetry"
    if harsh_brake:
        return f"{harsh_brake} harsh-brake event(s)"
    if harsh_corner:
        return f"{harsh_corner} fast-corner event(s)"
    if speeding_pct > 0:
        return "Speeding time detected"
    return "No aggregate risk event"


def _dominant_driver_state(summary: dict[str, Any]) -> str:
    distribution = _mapping(summary.get("state_distribution_pct"))
    if not distribution:
        return "unknown"
    state, _ = max(distribution.items(), key=lambda item: _finite(item[1]) or 0.0)
    if state == "alert":
        return "attentive"
    return state if state in {"attentive", "distracted", "drowsy", "unknown"} else "unknown"


def _max_speed(raw_frames: object) -> float | None:
    if not isinstance(raw_frames, list):
        return None
    speeds = []
    for frame in raw_frames:
        ego = _mapping(_mapping(frame).get("ego"))
        speed = _finite(ego.get("speed_kmh"))
        if speed is not None:
            speeds.append(max(0.0, min(300.0, speed)))
    return round(max(speeds), 1) if speeds else None


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _finite(value: object) -> float | None:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    return candidate if math.isfinite(candidate) else None


def _unit(value: object) -> float:
    candidate = _finite(value)
    return max(0.0, min(1.0, candidate)) if candidate is not None else 0.0


def _nonnegative_int(value: object) -> int:
    candidate = _finite(value)
    return max(0, round(candidate)) if candidate is not None else 0
