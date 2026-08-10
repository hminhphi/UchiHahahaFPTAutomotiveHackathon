"""YOLO-based detector that implements the DetectorClient protocol."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .types import Detection

DEFAULT_MODEL_PATH = Path(
    "artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt"
)

YOLO_CLASS_NAMES = {
    0: "Car",
    1: "Bus",
    2: "LongVehicle",
    3: "Motorcycle",
    4: "Cyclist",
    5: "Pedestrian",
}


class YoloDetector:
    """Runs YOLOv8-style model inference and converts results to Detection objects."""

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        device: str = "cpu",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> None:
        from ultralytics import YOLO

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self._model = YOLO(str(model_path))
        self._model.to(device)

    def __call__(self, image_bgr: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            image_bgr,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                object_type = YOLO_CLASS_NAMES.get(cls_id, f"class_{cls_id}")
                detections.append(
                    Detection(
                        object_type=object_type,
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        source="yolo",
                    )
                )
        return _deduplicate_by_class(detections)


def _deduplicate_by_class(
    detections: list[Detection], iou_threshold: float = 0.7
) -> list[Detection]:
    """Remove same-class boxes that survive the model's built-in NMS."""
    kept: list[Detection] = []
    for detection in sorted(detections, key=lambda item: item.confidence, reverse=True):
        if any(
            detection.object_type == existing.object_type
            and _bbox_iou(detection.bbox, existing.bbox) >= iou_threshold
            for existing in kept
        ):
            continue
        kept.append(detection)
    return kept


def _bbox_iou(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union > 0.0 else 0.0
