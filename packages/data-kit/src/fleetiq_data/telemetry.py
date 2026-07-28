"""Small, lossless-friendly normalization for organizer telemetry frames."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    """Normalized fields commonly used by FleetIQ scoring and visualization."""

    frame_id: int
    timestamp_s: float | None
    speed_mps: float | None
    longitudinal_accel_mps2: float | None
    lateral_accel_mps2: float | None
    min_ttc_s: float | None
    risk_score: float | None
    driver_state: str | None
    alertness_score: float | None
    raw: Mapping[str, Any]


def normalize_telemetry(frames: Sequence[Mapping[str, Any]]) -> list[TelemetryFrame]:
    """Normalize known frame fields while retaining each original frame mapping."""
    return [
        TelemetryFrame(
            frame_id=index,
            timestamp_s=_finite_float(frame.get("timestamp")),
            speed_mps=_finite_float(_nested_value(frame, "ego", "speed_mps"))
            or _finite_float(frame.get("speed"))
            or _kmh_to_mps(_nested_value(frame, "ego", "speed_kmh")),
            longitudinal_accel_mps2=_finite_float(
                _nested_value(frame, "ego", "longitudinal_accel")
            ),
            lateral_accel_mps2=_finite_float(_nested_value(frame, "ego", "lateral_accel")),
            min_ttc_s=_finite_float(frame.get("min_ttc")),
            risk_score=_finite_float(_nested_value(frame, "risk", "final_risk_score")),
            driver_state=_string_or_none(_nested_value(frame, "driver", "state")),
            alertness_score=_finite_float(_nested_value(frame, "driver", "alertness_score")),
            raw=frame,
        )
        for index, frame in enumerate(frames)
    ]


def _nested_value(frame: Mapping[str, Any], group: str, key: str) -> Any:
    section = frame.get(group)
    return section.get(key) if isinstance(section, Mapping) else None


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _kmh_to_mps(value: Any) -> float | None:
    parsed = _finite_float(value)
    return parsed / 3.6 if parsed is not None else None


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
