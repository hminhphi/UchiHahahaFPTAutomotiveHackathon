from __future__ import annotations

import importlib.util
from pathlib import Path


def load_generator_module():
    path = Path(__file__).with_name("generate_ai_artifacts.py")
    spec = importlib.util.spec_from_file_location("generate_ai_artifacts", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_kitti_label_excludes_boxes_at_or_below_30_pixels(tmp_path: Path) -> None:
    labels = tmp_path / "000000.txt"
    labels.write_text(
        "\n".join(
            (
                "Car 0 0 0 10 10 40 40",
                "Car 0 0 0 10 10 41 40",
                "Car 0 0 0 10 10 40 41",
                "Car 0 0 0 10 10 41 41",
            )
        ),
        encoding="utf-8",
    )

    generator = load_generator_module()

    detections = generator.parse_kitti_label(labels)

    assert len(detections) == 1
    assert detections[0]["x2"] - detections[0]["x1"] == 31
    assert detections[0]["y2"] - detections[0]["y1"] == 31


def test_discover_trip_dirs_always_selects_every_trip(tmp_path: Path) -> None:
    for name in ("T02d", "T01d", "not-a-trip"):
        (tmp_path / name).mkdir()

    generator = load_generator_module()

    assert [trip_dir.name for trip_dir in generator.discover_trip_dirs(tmp_path)] == ["T01d", "T02d"]


def test_road_analysis_discards_objects_outside_the_ego_lane() -> None:
    generator = load_generator_module()

    road = generator.generate_road_frame(
        0,
        [
            {"type": "Car", "x1": 80, "y1": 120, "x2": 140, "y2": 220},
            {"type": "Car", "x1": 270, "y1": 120, "x2": 350, "y2": 220},
        ],
        ego_speed_kmh=50,
    )

    assert len(road["detections"]) == 1
    assert road["detections"][0]["lane_relation"] == "in_lane"
    assert road["detections"][0]["bounding_box"]["x_min"] == 270


def test_fusion_uses_canonical_rules_for_in_lane_risk_events() -> None:
    generator = load_generator_module()

    fusion = generator.generate_fusion_frame(
        0,
        {"detections": [{"lane_relation": "in_lane", "ttc_s": 1.0}]},
        {"driver_state": {"state": "distracted"}},
        {"speed_kmh": 80, "longitudinal_accel_mps2": -4.5, "lateral_accel_mps2": 0},
    )

    assert fusion["risk_index"] == 70
    assert fusion["safety_score"] == 30
    assert fusion["severity"] == 5
    assert fusion["event_codes"] == ["short_ttc", "driver_distraction", "compound_risk", "speeding", "harsh_longitudinal_accel"]


def test_event_log_merges_short_gaps_without_dropping_later_events() -> None:
    generator = load_generator_module()

    events = generator.generate_event_log(
        "T01d",
        [
            {"frame_index": 0, "event_codes": ["speeding"], "severity": 2},
            {"frame_index": 5, "event_codes": [], "severity": 1},
            {"frame_index": 10, "event_codes": ["speeding"], "severity": 3},
            {"frame_index": 25, "event_codes": ["speeding"], "severity": 2},
        ],
    )

    assert [(event["frame_index"], event["end_frame_index"], event["severity"]) for event in events] == [(0, 10, 3), (25, 25, 2)]


def test_event_log_coalesces_repeated_dms_states_across_a_brief_transition() -> None:
    generator = load_generator_module()
    frames = [
        {"frame_index": frame_index, "event_codes": ["driver_drowsiness"], "severity": 3}
        for frame_index in range(15)
    ]
    frames.extend([
        *[
            {"frame_index": frame_index, "event_codes": ["driver_distraction"], "severity": 2}
            for frame_index in range(30, 45)
        ],
        *[
            {"frame_index": frame_index, "event_codes": ["driver_drowsiness"], "severity": 3}
            for frame_index in range(50, 65)
        ],
    ])

    events = generator.generate_event_log("T01d", frames)

    assert [(event["event_type"], event["frame_index"], event["end_frame_index"]) for event in events] == [
        ("driver_drowsiness", 0, 64),
        ("driver_distraction", 30, 44),
    ]
