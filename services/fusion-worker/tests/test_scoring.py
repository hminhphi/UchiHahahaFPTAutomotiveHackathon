from fleetiq_fusion.scoring import RiskScorer


def test_distraction_plus_short_ttc_increases_severity_once() -> None:
    result = RiskScorer().score(
        ttc_s=1.4,
        driver_state="distracted",
        speed_mps=18.0,
        lane_offset_m=0.2,
    )

    assert result.severity == 5
    assert result.explanation_codes == [
        "short_ttc",
        "driver_distraction",
        "compound_risk",
    ]


def test_score_is_bounded_and_penalties_are_explainable() -> None:
    result = RiskScorer().score(
        ttc_s=1.0,
        driver_state="drowsy",
        speed_mps=30.0,
        speed_limit_mps=15.0,
        lane_offset_m=1.2,
        lateral_accel_mps2=5.0,
    )

    assert 0 <= result.score <= 100
    assert set(result.penalties) == {"collision", "attention", "handling", "lane"}
    assert result.score == 100 - sum(result.penalties.values())
    assert result.severity == 5


def test_safe_frame_has_no_false_compound_risk() -> None:
    result = RiskScorer().score(
        ttc_s=6.0,
        driver_state="attentive",
        speed_mps=10.0,
        lane_offset_m=0.1,
    )

    assert result.severity == 1
    assert result.explanation_codes == []
    assert result.score == 100


def test_driver_distraction_alone_is_actionable() -> None:
    result = RiskScorer().score(
        ttc_s=None,
        driver_state="distracted",
        speed_mps=10.0,
        lane_offset_m=None,
    )

    assert result.severity == 2
    assert result.explanation_codes == ["driver_distraction"]
