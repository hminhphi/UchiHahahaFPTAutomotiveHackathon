import pandas as pd
import pytest

from fleetiq_training_dms.generalization_data import normalize_label, subject_split


def test_normalizes_five_source_states_to_three_training_classes():
    assert normalize_label("alert") == 0
    assert normalize_label("texting") == 1
    assert normalize_label("microsleep") == 2
    assert normalize_label("unknown") is None


def test_subject_split_never_shares_a_subject():
    records = pd.DataFrame({"subject_id": ["1", "1", "2"], "label": [0, 0, 1]})
    train, validation = subject_split(records, validation_subject="2")
    assert set(train.subject_id) == {"1"}
    assert set(validation.subject_id) == {"2"}


def test_subject_split_rejects_empty_side():
    records = pd.DataFrame({"subject_id": ["1"], "label": [0]})
    with pytest.raises(ValueError, match="validation subject"):
        subject_split(records, validation_subject="2")
