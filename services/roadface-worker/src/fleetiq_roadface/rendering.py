"""Road-facing evidence overlays."""

from __future__ import annotations

import cv2
import numpy as np

from .types import Detection, LaneEstimate

CLASS_COLORS = {
    "Car": (40, 210, 255),
    "Van": (80, 220, 160),
    "Truck": (80, 160, 255),
    "Pedestrian": (80, 90, 255),
    "Cyclist": (255, 160, 80),
    "Motorcycle": (255, 120, 180),
    "Bus": (50, 230, 230),
    "LongVehicle": (180, 120, 255),
}


def draw_overlay(
    image: np.ndarray,
    detections: list[Detection],
    lane: LaneEstimate | None,
) -> np.ndarray:
    output = image.copy()
    if lane is not None:
        output = _blend_mask(output, lane.road_mask, (0, 150, 0), 0.18)
        output = _blend_mask(output, lane.vertical_corridor_mask, (180, 0, 0), 0.08)
        output = _blend_mask(output, lane.corridor_mask, (220, 180, 0), 0.28)
        if lane.lane_mask is not None:
            lane_color = np.zeros_like(output)
            lane_color[:, :, 1] = 210
            lane_color[:, :, 2] = 255
            output = np.where(lane.lane_mask[:, :, None] > 0, lane_color, output)
        for segment in lane.line_segments:
            cv2.line(output, segment[:2], segment[2:], (30, 220, 255), 2, cv2.LINE_AA)

    for detection in detections:
        color = CLASS_COLORS.get(detection.object_type, (220, 220, 220))
        x1, y1, x2, y2 = [round(value) for value in detection.bbox]
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        distance = (
            "--" if detection.distance_m is None else f"{detection.distance_m:.1f}m"
        )
        relative = (
            "--"
            if detection.relative_speed_mps is None
            else f"{detection.relative_speed_mps:+.1f}m/s"
        )
        ttc = "--" if detection.ttc_s is None else f"{detection.ttc_s:.1f}s"
        draw_tag(
            output,
            (
                f"#{detection.track_id or 0} {detection.object_type} {distance} "
                f"rel {relative} TTC {ttc}"
            ),
            (x1, max(16, y1 - 5)),
            color,
        )

    offset = "--"
    if lane is not None and lane.lane_offset_m is not None:
        offset = f"{lane.lane_offset_m:+.2f} m"
    draw_tag(output, f"lane offset {offset}", (14, 28), (30, 220, 255))
    return output


def draw_tag(
    image: np.ndarray,
    text: str,
    anchor: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    x, y = anchor
    size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.46, 1)[0]
    x = int(np.clip(x, 0, max(0, image.shape[1] - size[0] - 8)))
    y = int(np.clip(y, size[1] + 8, image.shape[0] - 2))
    cv2.rectangle(
        image,
        (x, y - size[1] - 8),
        (x + size[0] + 8, y + 4),
        color,
        -1,
    )
    cv2.putText(
        image,
        text,
        (x + 4, y - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (15, 20, 25),
        1,
        cv2.LINE_AA,
    )


def _blend_mask(
    image: np.ndarray,
    mask: np.ndarray | None,
    color: tuple[int, int, int],
    alpha: float,
) -> np.ndarray:
    if mask is None:
        return image
    layer = np.zeros_like(image)
    layer[:, :] = color
    blended = cv2.addWeighted(image, 1.0 - alpha, layer, alpha, 0)
    return np.where(mask[:, :, None] > 0, blended, image)
