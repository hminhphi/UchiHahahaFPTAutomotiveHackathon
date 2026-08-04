from pathlib import Path
from types import SimpleNamespace

from fleetiq_training_dms.phone_detector import PhoneUseDetector, PhoneUseSmoother


class Values:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeModel:
    def __init__(self, result):
        self.result = result

    def predict(self, **kwargs):
        return [self.result]


def test_phone_smoother_requires_three_positive_valid_frames():
    smoother = PhoneUseSmoother()
    assert [smoother.update(value) for value in (True, None, True)] == [None, None, None]
    assert smoother.update(True) is True


def test_phone_smoother_returns_false_after_three_valid_negative_frames():
    smoother = PhoneUseSmoother()
    assert [smoother.update(False) for _ in range(3)] == [None, None, False]


def test_detector_keeps_only_confident_cell_phone(tmp_path: Path):
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"frame")
    result = SimpleNamespace(
        names={0: "person", 67: "cell phone"},
        boxes=SimpleNamespace(cls=Values([0, 67]), conf=Values([0.99, 0.72])),
    )
    detector = PhoneUseDetector(tmp_path / "unused.pt", model=FakeModel(result))
    assert detector.detect(image) is True


def test_detector_returns_none_when_unavailable(tmp_path: Path):
    assert PhoneUseDetector(tmp_path / "missing.pt").detect(tmp_path / "frame.jpg") is None
