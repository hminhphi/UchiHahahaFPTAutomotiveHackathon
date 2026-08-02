from fleetiq_api.trajectory import build_trajectory


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
