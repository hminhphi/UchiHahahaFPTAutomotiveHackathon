import pandas as pd

from fleetiq_training_dms.pseudo_labels import apply_geometry_pseudo_labels


def test_geometry_pseudo_labels_assign_expected_states() -> None:
    features = pd.DataFrame(
        [
            {"face_detected": True, "ear": 0.29, "mar": 0.18, "perclos": 0.0, "pitch": 0.0, "yaw": 0.0},
            {"face_detected": True, "ear": 0.29, "mar": 0.18, "perclos": 0.0, "pitch": 0.0, "yaw": 31.0},
            {"face_detected": True, "ear": 0.17, "mar": 0.18, "perclos": 0.65, "pitch": 0.0, "yaw": 0.0},
            {"face_detected": True, "ear": 0.29, "mar": 0.62, "perclos": 0.0, "pitch": 0.0, "yaw": 0.0},
            {"face_detected": False, "ear": None, "mar": None, "perclos": None, "pitch": None, "yaw": None},
        ]
    )

    labeled = apply_geometry_pseudo_labels(features)

    assert labeled["state_label"].tolist() == [0, 1, 3, 4, -1]
    assert labeled["label_source"].tolist() == [
        "geometry_rules_v1",
        "geometry_rules_v1",
        "geometry_rules_v1",
        "geometry_rules_v1",
        "excluded_no_face",
    ]


def test_geometry_pseudo_labels_use_15_frame_smoothed_pose() -> None:
    features = pd.DataFrame(
        [{
            "face_detected": True,
            "ear": 0.29,
            "ear_mean_5": 0.29,
            "mar": 0.18,
            "mar_mean_5": 0.18,
            "perclos": 0.0,
            "pitch": 0.0,
            "pitch_mean_5": 0.0,
            "yaw": 31.0,
            "yaw_mean_5": 31.0 / 15.0,
        }]
    )

    labeled = apply_geometry_pseudo_labels(features)

    assert labeled["state_label"].tolist() == [0]
