from __future__ import annotations

from fleetiq_roadface.tracking import ClosingSpeedEstimator, ObstacleTracker
from fleetiq_roadface.types import Detection


def test_closing_speed_and_ttc_use_frame_delta() -> None:
    estimator = ClosingSpeedEstimator(smoothing_alpha=1.0)
    estimator.update(track_id=7, timestamp_s=0.0, distance_m=20.0)
    state = estimator.update(track_id=7, timestamp_s=0.5, distance_m=18.0)
    assert state.relative_speed_mps == 4.0
    assert state.ttc_s == 4.5


def test_non_increasing_timestamp_does_not_invent_motion() -> None:
    estimator = ClosingSpeedEstimator(smoothing_alpha=1.0)
    estimator.update(track_id=7, timestamp_s=1.0, distance_m=20.0)
    state = estimator.update(track_id=7, timestamp_s=1.0, distance_m=18.0)
    assert state.relative_speed_mps is None
    assert state.ttc_s is None


def test_non_increasing_timestamp_does_not_replace_valid_history() -> None:
    estimator = ClosingSpeedEstimator(smoothing_alpha=1.0)
    estimator.update(track_id=7, timestamp_s=0.0, distance_m=20.0)
    estimator.update(track_id=7, timestamp_s=0.0, distance_m=10.0)

    state = estimator.update(track_id=7, timestamp_s=1.0, distance_m=18.0)

    assert state.relative_speed_mps == 2.0
    assert state.ttc_s == 9.0


def test_implausible_same_class_jump_starts_fresh_track_without_ttc() -> None:
    tracker = ObstacleTracker(smoothing_alpha=1.0)
    first = Detection("Car", (0.0, 0.0, 20.0, 20.0), distance_m=40.0)
    second = Detection("Car", (1.0, 0.0, 21.0, 20.0), distance_m=35.0)
    replacement = Detection("Car", (1.0, 0.0, 21.0, 20.0), distance_m=2.0)
    tracker.update([first], timestamp_s=0.0)
    tracker.update([second], timestamp_s=1.0)

    tracker.update([replacement], timestamp_s=1.1)

    assert replacement.track_id != second.track_id
    assert replacement.relative_speed_mps is None
    assert replacement.ttc_s is None


def test_plausible_same_class_motion_keeps_track_and_ttc() -> None:
    tracker = ObstacleTracker(smoothing_alpha=1.0)
    first = Detection("Car", (0.0, 0.0, 20.0, 20.0), distance_m=40.0)
    second = Detection("Car", (1.0, 0.0, 21.0, 20.0), distance_m=35.0)
    third = Detection("Car", (2.0, 0.0, 22.0, 20.0), distance_m=30.0)

    tracker.update([first], timestamp_s=0.0)
    tracker.update([second], timestamp_s=1.0)
    tracker.update([third], timestamp_s=2.0)

    assert first.track_id == second.track_id == third.track_id
    assert third.relative_speed_mps == 5.0
    assert third.ttc_s == 6.0


def test_missing_distance_clears_motion_before_next_valid_measurement() -> None:
    tracker = ObstacleTracker(smoothing_alpha=1.0)
    first = Detection("Car", (0.0, 0.0, 20.0, 20.0), distance_m=40.0)
    missing = Detection("Car", (1.0, 0.0, 21.0, 20.0), distance_m=None)
    resumed = Detection("Car", (2.0, 0.0, 22.0, 20.0), distance_m=30.0)

    tracker.update([first], timestamp_s=0.0)
    tracker.update([missing], timestamp_s=1.0)
    tracker.update([resumed], timestamp_s=2.0)

    assert first.track_id == missing.track_id == resumed.track_id
    assert resumed.relative_speed_mps is None
    assert resumed.ttc_s is None
