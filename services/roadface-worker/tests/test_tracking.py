from __future__ import annotations

from fleetiq_roadface.tracking import ClosingSpeedEstimator


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
