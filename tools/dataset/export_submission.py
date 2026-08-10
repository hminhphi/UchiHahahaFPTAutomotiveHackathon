"""Build organizer-format submission CSVs from FleetIQ's per-frame predictions.

The hackathon grades a CSV per scored trip, not the dashboard. Required
columns and semantics come from
``data/team-kit/Package_starterkit/package_starterkit/README.md`` and
``HUONG_DAN_NGUOI_MOI.md``:

    frame_id,timestamp,predicted_ttc,predicted_driver_state,predicted_risk_score

- One row per frame, in ``frame_id`` order, with exactly the trip's frame
  count (1800 for every T0Xd trip, including T02d despite its "DEBUG 30s"
  metadata description).
- ``predicted_ttc``: seconds, or the literal ``inf`` (never a blank cell)
  when nothing is detected in the collision cone.
- ``predicted_driver_state``: exactly one of
  ``alert|drowsy|yawning|distracted|microsleep`` — any other string scores
  as a wrong prediction under Challenge 2, so unmapped/unknown states must
  be normalized to a valid label rather than passed through.
- ``predicted_risk_score``: 0-100.
- Files are written as ``predictions/<team>/<trip_id>.csv``.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

SUBMISSION_COLUMNS: tuple[str, ...] = (
    "frame_id",
    "timestamp",
    "predicted_ttc",
    "predicted_driver_state",
    "predicted_risk_score",
)

# The only five labels evaluation.py's Challenge 2 scorer recognizes. Any
# other string (including "unknown" and "attentive") is a guaranteed miss.
ACCEPTED_DRIVER_STATES: frozenset[str] = frozenset(
    {"alert", "drowsy", "yawning", "distracted", "microsleep"}
)

# FleetIQ's own DMS pipeline uses "attentive"/"unknown" internally; map those
# onto the organizer's label set instead of emitting an invalid string.
_DRIVER_STATE_ALIASES: dict[str, str] = {
    "attentive": "alert",
}

_MIN_TTC_CONFIDENCE = 0.5

# Matches team_kit/baseline_ttc_predictor.py's DEFAULT_ROI: centered
# horizontally, lower-middle vertically. Lane detection (Hough-transform
# based) only succeeds on a fraction of frames in practice, so a fixed ROI
# in the organizer's own convention is the reliable way to approximate the
# ground truth's "collision cone" scope.
_ROI_X_START_FRAC = 0.35
_ROI_X_END_FRAC = 0.65
_ROI_Y_START_FRAC = 0.50
_ROI_Y_END_FRAC = 0.85


@dataclass(frozen=True, slots=True)
class FramePrediction:
    frame_id: int
    timestamp_s: float
    predicted_ttc_s: float
    predicted_driver_state: str
    predicted_risk_score: float


def normalize_driver_state(value: str | None) -> str:
    """Map any FleetIQ-internal label onto one of the five accepted classes.

    Falls back to "alert" for anything unrecognized (including "unknown" and
    a missing/empty value) because leaving an invalid string in the column
    guarantees a wrong prediction for that frame under Challenge 2, whereas a
    baseline guess at least has a chance of matching low-risk frames, which
    make up most of a trip.
    """
    candidate = (value or "").strip().lower()
    candidate = _DRIVER_STATE_ALIASES.get(candidate, candidate)
    return candidate if candidate in ACCEPTED_DRIVER_STATES else "alert"


def frame_min_ttc(
    detections: list[dict],
    *,
    image_width: int,
    image_height: int,
) -> float:
    """Mirror the ground truth's definition: minimum TTC among detections
    inside a centered ROI (the same fixed collision-cone approximation used
    by ``team_kit/baseline_ttc_predictor.py``'s ``DEFAULT_ROI``). Matches
    `frame.min_ttc` in `team_kit/dataset_loader.py`, which is scoped to the
    collision cone, not every detected object in the frame.
    """
    roi_x_start = _ROI_X_START_FRAC * image_width
    roi_x_end = _ROI_X_END_FRAC * image_width
    roi_y_start = _ROI_Y_START_FRAC * image_height
    roi_y_end = _ROI_Y_END_FRAC * image_height

    candidates = []
    for detection in detections:
        if detection.get("ttc_s") is None:
            continue
        if (detection.get("distance_confidence") or 0.0) < _MIN_TTC_CONFIDENCE:
            continue
        x_min, y_min, x_max, y_max = detection["bbox"]
        center_x = (x_min + x_max) / 2.0
        center_y = (y_min + y_max) / 2.0
        if not (roi_x_start <= center_x <= roi_x_end and roi_y_start <= center_y <= roi_y_end):
            continue
        candidates.append(detection["ttc_s"])
    return min(candidates) if candidates else float("inf")


def write_submission_csv(path: Path, predictions: list[FramePrediction]) -> None:
    seen: set[int] = set()
    for prediction in predictions:
        if prediction.frame_id in seen:
            raise ValueError(f"duplicate frame_id in submission: {prediction.frame_id}")
        seen.add(prediction.frame_id)

    ordered = sorted(predictions, key=lambda prediction: prediction.frame_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SUBMISSION_COLUMNS)
        for prediction in ordered:
            ttc = prediction.predicted_ttc_s
            ttc_cell = "inf" if ttc != ttc or ttc == float("inf") else f"{ttc:.3f}"
            risk = max(0.0, min(100.0, prediction.predicted_risk_score))
            writer.writerow(
                [
                    prediction.frame_id,
                    f"{prediction.timestamp_s:.3f}",
                    ttc_cell,
                    normalize_driver_state(prediction.predicted_driver_state),
                    f"{risk:.1f}",
                ]
            )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", required=True, help="Team name used in the output path.")
    parser.add_argument(
        "--trip",
        action="append",
        required=True,
        help="Scored trip id (e.g. T01d). Repeat for multiple trips.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted"),
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/trips"),
        help="Root containing refreshed road, DMS, and fusion artifacts.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("predictions"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        from tools.dataset.export_submission_pipeline import export_trip
    except ModuleNotFoundError:
        from export_submission_pipeline import export_trip

    for trip_id in args.trip:
        output_path = args.output_root / args.team / f"{trip_id}.csv"
        export_trip(
            trip_id=trip_id,
            dataset_root=args.dataset_root,
            output_path=output_path,
            artifact_root=args.artifact_root,
        )
        print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
