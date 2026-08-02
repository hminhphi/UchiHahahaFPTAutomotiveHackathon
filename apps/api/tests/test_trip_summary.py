from fleetiq_api.trip_summary import build_trip_summary


def test_trip_summary_scores_organizer_aggregate_with_explicit_penalties() -> None:
    summary = build_trip_summary(
        "T01-Sample",
        {
            "trip_aggregate": {
                "near_miss_count": 2,
                "harsh_brake_count": 3,
                "harsh_corner_count": 1,
                "speeding_pct_time": 0,
                "max_risk_score": 60,
            },
            "driver_summary": {
                "average_alertness_score": 0.75,
                "state_distribution_pct": {"alert": 60, "distracted": 40},
            },
            "frames": [{"ego": {"speed_kmh": 12}}, {"ego": {"speed_kmh": 34.4}}],
        },
    )

    assert summary.safety_score == 84
    assert summary.severity == 4
    assert summary.driver_state == "attentive"
    assert summary.max_speed_kmh == 34.4
    assert summary.latest_alert == "2 near-miss event(s) in organizer telemetry"
