import json

import pytest

from fleetiq_training_dms.prepare_vicomtech import labels_from_openlabel


def test_openlabel_intervals_map_to_fleetiq_states(tmp_path) -> None:
    annotation = tmp_path / "sample_rgb_ann_drowsiness.json"
    annotation.write_text(json.dumps({"openlabel": {"actions": {
        "0": {"type": "eyes_state/close", "frame_intervals": [{"frame_start": 2, "frame_end": 14}]},
        "1": {"type": "yawning/Yawning", "frame_intervals": [{"frame_start": 8, "frame_end": 10}]},
    }}}), encoding="utf-8")
    assert labels_from_openlabel(annotation, frame_count=20, fps=25).tolist() == [0, 0, 2, 2, 2, 2, 2, 2, 4, 4, 4, 2, 2, 2, 2, 0, 0, 0, 0, 0]


def test_unreadable_video_cannot_create_negative_label_array(tmp_path) -> None:
    annotation = tmp_path / "sample_rgb_ann_drowsiness.json"
    annotation.write_text('{"openlabel": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="no readable frames"):
        labels_from_openlabel(annotation, frame_count=-1, fps=25)
