"""Submission CSV export must match the organizer's required format exactly."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from tools.dataset.export_submission import (
    SUBMISSION_COLUMNS,
    FramePrediction,
    frame_min_ttc,
    normalize_driver_state,
    write_submission_csv,
)


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_header_matches_the_required_submission_columns(tmp_path: Path) -> None:
    target = tmp_path / "T01d.csv"

    write_submission_csv(target, [FramePrediction(0, 0.0, float("inf"), "alert", 5.0)])

    header, _ = _read(target)
    assert header == [
        "frame_id",
        "timestamp",
        "predicted_ttc",
        "predicted_driver_state",
        "predicted_risk_score",
    ]
    assert header == list(SUBMISSION_COLUMNS)


def test_missing_ttc_is_written_as_inf_not_blank(tmp_path: Path) -> None:
    """The checklist requires 'inf', never an empty cell, when nothing is detected."""
    target = tmp_path / "T01d.csv"

    write_submission_csv(target, [FramePrediction(0, 0.0, float("inf"), "alert", 5.0)])

    _, rows = _read(target)
    assert rows[0]["predicted_ttc"] == "inf"


def test_writes_one_row_per_frame_in_frame_id_order(tmp_path: Path) -> None:
    target = tmp_path / "T01d.csv"
    predictions = [
        FramePrediction(2, 0.10, 3.0, "alert", 10.0),
        FramePrediction(0, 0.00, 1.0, "drowsy", 90.0),
        FramePrediction(1, 0.05, 2.0, "alert", 50.0),
    ]

    write_submission_csv(target, predictions)

    _, rows = _read(target)
    assert [row["frame_id"] for row in rows] == ["0", "1", "2"]
    assert [row["timestamp"] for row in rows] == ["0.000", "0.050", "0.100"]


def test_driver_state_uses_only_the_five_accepted_labels() -> None:
    """Challenge 2 scores a mislabelled string as a wrong prediction."""
    assert normalize_driver_state("attentive") == "alert"
    assert normalize_driver_state("Alert") == "alert"
    assert normalize_driver_state("drowsy") == "drowsy"
    assert normalize_driver_state("yawning") == "yawning"
    assert normalize_driver_state("distracted") == "distracted"
    assert normalize_driver_state("microsleep") == "microsleep"


def test_unknown_driver_state_falls_back_to_alert() -> None:
    """'unknown' is not an accepted label, so it would always score as wrong."""
    assert normalize_driver_state("unknown") == "alert"
    assert normalize_driver_state("") == "alert"
    assert normalize_driver_state(None) == "alert"


def test_min_ttc_only_counts_objects_inside_the_roi() -> None:
    """Ground-truth min_ttc is the collision-cone minimum; approximate that
    with a fixed centered ROI, since lane detection is unreliable and the
    baseline predictor uses the same fixed-ROI approach."""
    detections = [
        {"bbox": (0, 0, 30, 30), "ttc_s": 0.5, "distance_confidence": 0.9},  # far left, outside ROI
        {"bbox": (280, 200, 360, 280), "ttc_s": 2.5, "distance_confidence": 0.9},  # centered
    ]

    assert frame_min_ttc(detections, image_width=640, image_height=360) == 2.5


def test_min_ttc_is_infinite_when_no_object_is_in_the_roi() -> None:
    detections = [{"bbox": (0, 0, 30, 30), "ttc_s": 0.5, "distance_confidence": 0.9}]

    assert math.isinf(frame_min_ttc(detections, image_width=640, image_height=360))


def test_min_ttc_ignores_low_confidence_distance_estimates() -> None:
    detections = [
        {"bbox": (280, 200, 360, 280), "ttc_s": 1.0, "distance_confidence": 0.1},
    ]

    assert math.isinf(frame_min_ttc(detections, image_width=640, image_height=360))


def test_min_ttc_ignores_detections_without_a_ttc() -> None:
    detections = [
        {"bbox": (280, 200, 360, 280), "ttc_s": None, "distance_confidence": 0.9},
    ]

    assert math.isinf(frame_min_ttc(detections, image_width=640, image_height=360))


def test_risk_score_is_clamped_into_the_documented_range(tmp_path: Path) -> None:
    target = tmp_path / "T01d.csv"

    write_submission_csv(
        target,
        [
            FramePrediction(0, 0.0, float("inf"), "alert", -20.0),
            FramePrediction(1, 0.05, float("inf"), "alert", 250.0),
        ],
    )

    _, rows = _read(target)
    assert rows[0]["predicted_risk_score"] == "0.0"
    assert rows[1]["predicted_risk_score"] == "100.0"


def test_rejects_duplicate_frame_ids(tmp_path: Path) -> None:
    """A duplicated frame would silently change the submitted row count."""
    target = tmp_path / "T01d.csv"

    with pytest.raises(ValueError, match="duplicate"):
        write_submission_csv(
            target,
            [
                FramePrediction(0, 0.0, 1.0, "alert", 5.0),
                FramePrediction(0, 0.0, 2.0, "alert", 5.0),
            ],
        )


def test_risk_score_rises_for_a_near_collision() -> None:
    from tools.dataset.export_submission_pipeline import _risk_score

    assert _risk_score(1.0, "alert") > _risk_score(10.0, "alert")


def test_risk_score_rises_for_drowsy_even_with_a_safe_ttc() -> None:
    from tools.dataset.export_submission_pipeline import _risk_score

    assert _risk_score(float("inf"), "drowsy") > _risk_score(float("inf"), "alert")


def test_risk_score_takes_the_worse_of_road_and_driver_risk() -> None:
    from tools.dataset.export_submission_pipeline import _risk_score

    combined = _risk_score(1.0, "drowsy")
    road_only = _risk_score(1.0, "alert")
    driver_only = _risk_score(float("inf"), "drowsy")

    assert combined == max(road_only, driver_only)
