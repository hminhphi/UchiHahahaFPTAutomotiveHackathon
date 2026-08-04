"""Optional cell-phone detection for saved driver-camera frames."""

from collections import deque
from pathlib import Path
from typing import Any


class PhoneUseSmoother:
    """Return a stable phone signal after three positive valid observations."""

    def __init__(self, window_size: int = 5, min_positive: int = 3) -> None:
        if min_positive < 1 or window_size < min_positive:
            raise ValueError("phone smoothing requires 1 <= min_positive <= window_size")
        self._values: deque[bool] = deque(maxlen=window_size)
        self._min_positive = min_positive

    def update(self, detected: bool | None) -> bool | None:
        if detected is not None:
            self._values.append(detected)
        if len(self._values) < self._min_positive:
            return None
        return sum(self._values) >= self._min_positive


class PhoneUseDetector:
    """Best-effort YOLO cell-phone detector with a null fallback."""

    def __init__(self, model_path: Path, confidence: float = 0.40, model: Any = None) -> None:
        if not 0 <= confidence <= 1:
            raise ValueError("phone confidence must be between zero and one")
        self._confidence = confidence
        self._model = model
        if self._model is None and model_path.is_file():
            try:
                from ultralytics import YOLO

                self._model = YOLO(str(model_path))
            except Exception:  # noqa: BLE001 - optional model boundary
                self._model = None

    def detect(self, image_path: Path) -> bool | None:
        if self._model is None or not image_path.is_file():
            return None
        try:
            result = self._model.predict(source=str(image_path), verbose=False)[0]
            classes = result.boxes.cls.tolist()
            confidences = result.boxes.conf.tolist()
            return any(
                result.names[int(class_id)] == "cell phone" and score >= self._confidence
                for class_id, score in zip(classes, confidences, strict=True)
            )
        except Exception:  # noqa: BLE001 - optional model boundary
            return None
