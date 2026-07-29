import pytest
from fleetiq_dms.smoothing import StateSmoother


def test_single_drowsy_spike_does_not_flip_state() -> None:
    smoother = StateSmoother(window_size=5, min_votes=3)
    states = ["attentive", "attentive", "drowsy", "attentive", "attentive"]

    assert [smoother.update(state) for state in states][-1] == "attentive"


def test_state_changes_only_after_minimum_votes() -> None:
    smoother = StateSmoother(window_size=5, min_votes=3)

    assert smoother.update("drowsy") == "unknown"
    assert smoother.update("drowsy") == "unknown"
    assert smoother.update("drowsy") == "drowsy"


@pytest.mark.parametrize("window_size,min_votes", [(0, 1), (3, 0), (3, 4)])
def test_invalid_smoothing_configuration_is_rejected(
    window_size: int,
    min_votes: int,
) -> None:
    with pytest.raises(ValueError):
        StateSmoother(window_size=window_size, min_votes=min_votes)
