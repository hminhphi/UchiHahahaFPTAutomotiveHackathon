"""Materialize one trip's submission rows from refreshed FleetIQ artifacts.

Kept separate from ``export_submission.py`` so the organizer CSV rules stay
importable (and unit-testable) without loading model runtimes.

Two properties matter for grading and are enforced here:

1. **Every frame gets a row.** The organizer checklist requires the CSV to
   have exactly the trip's frame count. Frames the perception stack cannot
   process (unreadable image, no detection, no face) still emit a row with
   ``inf`` TTC and a fallback driver state, rather than being dropped.
2. **TTC matches the ground truth's definition.** ``frame.min_ttc`` in the
   organizer's loader is the minimum over the *collision cone*, so
   ``frame_min_ttc`` filters to in-lane, distance-confident detections only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fleetiq_data import DatasetPaths, load_trip_document, resolve_trip

try:
    from tools.dataset.export_submission import (
        FramePrediction,
        frame_min_ttc,
        write_submission_csv,
    )
except ModuleNotFoundError:
    from export_submission import FramePrediction, frame_min_ttc, write_submission_csv

# Mirrors evaluation.py's Challenge 3 reconstruction, which is itself a copy of
# the organizer's BehaviorScorer thresholds. Risk score is a per-frame value in
# the CSV, but Challenge 3 is graded per trip and does not read these numbers
# (only the column's presence opts the trip in), so this stays a transparent
# severity signal rather than a fitted quantity.
_NEAR_MISS_TTC_SEC = 1.5
_HIGH_RISK_TTC_SEC = 2.5
_MONITOR_TTC_SEC = 4.0

_DROWSY_STATES = frozenset({"drowsy", "microsleep", "yawning"})


def _risk_score(min_ttc_s: float, driver_state: str) -> float:
    """Blend collision urgency with driver impairment into a 0-100 severity."""
    if math.isinf(min_ttc_s):
        road_risk = 0.0
    elif min_ttc_s < _NEAR_MISS_TTC_SEC:
        road_risk = 95.0
    elif min_ttc_s < _HIGH_RISK_TTC_SEC:
        road_risk = 70.0
    elif min_ttc_s < _MONITOR_TTC_SEC:
        road_risk = 40.0
    else:
        road_risk = 10.0

    if driver_state in _DROWSY_STATES:
        driver_risk = 80.0
    elif driver_state == "distracted":
        driver_risk = 60.0
    else:
        driver_risk = 10.0

    return max(road_risk, driver_risk)


def _read_artifact(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _prediction_from_artifacts(
    artifact_root: Path,
    trip_id: str,
    frame_id: int,
) -> tuple[float, str, float]:
    frame_name = f"{frame_id:06d}.json"
    analysis_root = artifact_root / trip_id / "analysis"
    road = _read_artifact(analysis_root / "road" / frame_name)
    dms = _read_artifact(analysis_root / "dms" / frame_name)
    fusion = _read_artifact(analysis_root / "fusion" / frame_name)

    detections = []
    for detection in road.get("detections", []):
        box = detection.get("bounding_box")
        if not isinstance(box, dict):
            continue
        try:
            detections.append(
                {
                    "bbox": (
                        float(box["x_min"]),
                        float(box["y_min"]),
                        float(box["x_max"]),
                        float(box["y_max"]),
                    ),
                    "ttc_s": detection.get("ttc_s"),
                    "distance_confidence": detection.get("distance_confidence"),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    min_ttc = frame_min_ttc(detections, image_width=640, image_height=360)
    driver_state = (dms.get("driver_state") or {}).get("state", "alert")
    try:
        risk_score = float(fusion.get("risk_index"))
    except (TypeError, ValueError):
        risk_score = _risk_score(min_ttc, str(driver_state))
    return min_ttc, str(driver_state), risk_score


def export_trip(
    *,
    trip_id: str,
    dataset_root: Path,
    output_path: Path,
    artifact_root: Path,
) -> Path:
    trip = resolve_trip(DatasetPaths(dataset_root), trip_id)
    document = load_trip_document(trip)
    raw_frames = document.get("frames", [])
    if not raw_frames:
        raise ValueError(f"Trip {trip_id} has no frames")

    predictions: list[FramePrediction] = []
    for index, raw_frame in enumerate(raw_frames):
        frame_id = int(raw_frame.get("frame_id", index))
        timestamp_s = float(raw_frame.get("timestamp", index / 20.0))
        min_ttc, driver_state, risk_score = _prediction_from_artifacts(
            artifact_root, trip_id, frame_id
        )
        predictions.append(
            FramePrediction(
                frame_id=frame_id,
                timestamp_s=timestamp_s,
                predicted_ttc_s=min_ttc,
                predicted_driver_state=driver_state,
                predicted_risk_score=risk_score,
            )
        )

    write_submission_csv(output_path, predictions)
    return output_path
