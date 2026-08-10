import math

from fleetiq_api.trajectory import build_trajectory


def _kinematic_frames(lateral_accel: float, count: int = 40) -> dict:
    """Frames without ego.location, as shipped for the scored T0Xd trips."""
    return {
        "frames": [
            {
                "frame_id": index,
                "timestamp": round(index * 0.05, 2),
                "ego": {
                    "speed_kmh": 36.0,
                    "longitudinal_accel": 0.0,
                    "lateral_accel": lateral_accel,
                },
            }
            for index in range(count)
        ]
    }


def test_trajectory_uses_world_positions_and_bounds_acceleration() -> None:
    result = build_trajectory(
        "T01-Sample",
        {
            "frames": [
                {
                    "frame_id": 4,
                    "timestamp": 0.2,
                    "ego": {
                        "speed_kmh": 0,
                        "longitudinal_accel": 0,
                        "lateral_accel": 0,
                        "location": {"x": 10, "y": 20},
                    },
                },
                {
                    "frame_id": 5,
                    "timestamp": 0.25,
                    "ego": {
                        "speed_kmh": 100,
                        "longitudinal_accel": -100,
                        "lateral_accel": 7,
                        "location": {"x": 13, "y": 24},
                    },
                    "behavior_flags": {"harsh_brake": True},
                    "min_ttc": 1.25,
                    "headway_sec": 2.5,
                    "driver": {"state": "Alert", "alertness_score": 1.5},
                    "risk": {"final_risk_score": 12.5},
                    "events_active": [{"event_type": "near_miss"}],
                },
            ]
        },
    )

    assert result.distance_m == 5
    assert result.max_speed_kmh == 100
    assert result.max_lateral_accel_mps2 == 7
    assert result.points[1].longitudinal_accel_mps2 == -12
    assert result.points[1].min_ttc_s == 1.25
    assert result.points[1].driver_state == "alert"
    assert result.points[1].driver_alertness == 1
    assert result.points[1].active_event_types == ("near_miss",)
    assert result.points[1].events == ("harsh_brake", "fast_corner")


def test_trajectory_reconstructs_geometry_when_location_is_redacted() -> None:
    result = build_trajectory("T01d", _kinematic_frames(lateral_accel=0.0))
    assert len(result.points) == 40
    assert result.distance_m > 15
    assert result.max_speed_kmh == 36


def test_straight_driving_reconstructs_a_straight_path() -> None:
    result = build_trajectory("T01d", _kinematic_frames(lateral_accel=0.0))
    lateral_offsets = {round(point.y_m, 6) for point in result.points}
    assert lateral_offsets == {0.0}
    assert result.points[-1].x_m > result.points[0].x_m


def test_positive_lateral_acceleration_curves_left() -> None:
    result = build_trajectory("T01d", _kinematic_frames(lateral_accel=2.0))
    assert result.points[-1].y_m > 0


def test_negative_lateral_acceleration_curves_right() -> None:
    result = build_trajectory("T01d", _kinematic_frames(lateral_accel=-2.0))
    assert result.points[-1].y_m < 0


def test_opposite_turns_are_mirror_images() -> None:
    left = build_trajectory("T01d", _kinematic_frames(lateral_accel=2.0))
    right = build_trajectory("T01d", _kinematic_frames(lateral_accel=-2.0))
    assert math.isclose(left.points[-1].y_m, -right.points[-1].y_m, abs_tol=1e-9)
    assert math.isclose(left.points[-1].x_m, right.points[-1].x_m, abs_tol=1e-9)


def test_stationary_frames_do_not_accumulate_heading_drift() -> None:
    document = {
        "frames": [
            {
                "frame_id": index,
                "timestamp": round(index * 0.05, 2),
                "ego": {"speed_kmh": 0.0, "longitudinal_accel": 0.0, "lateral_accel": 3.0},
            }
            for index in range(40)
        ]
    }
    result = build_trajectory("T01d", document)
    assert result.distance_m == 0
    assert {round(point.x_m, 6) for point in result.points} == {0.0}
    assert {round(point.y_m, 6) for point in result.points} == {0.0}


def test_recorded_positions_take_priority_over_reconstruction() -> None:
    document = {
        "frames": [
            {
                "frame_id": 0,
                "timestamp": 0.0,
                "ego": {"speed_kmh": 36.0, "longitudinal_accel": 0.0, "lateral_accel": 5.0, "location": {"x": 100.0, "y": 200.0}},
            },
            {
                "frame_id": 1,
                "timestamp": 0.05,
                "ego": {"speed_kmh": 36.0, "longitudinal_accel": 0.0, "lateral_accel": 5.0, "location": {"x": 103.0, "y": 204.0}},
            },
        ]
    }
    result = build_trajectory("T01-Sample", document)
    assert (result.points[0].x_m, result.points[0].y_m) == (100.0, 200.0)
    assert (result.points[1].x_m, result.points[1].y_m) == (103.0, 204.0)
    assert result.distance_m == 5
