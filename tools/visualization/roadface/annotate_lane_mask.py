from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from fleetiq_training_roadface.experimental import find_image, read_image, resolve_trip


WINDOW_NAME = "FleetIQ manual lane annotation"
LEFT_COLOR = (0, 210, 255)   # Yellow in BGR.
RIGHT_COLOR = (255, 100, 255)  # Magenta in BGR.


@dataclass
class Annotation:
    left_points: list[tuple[int, int]] = field(default_factory=list)
    right_points: list[tuple[int, int]] = field(default_factory=list)

    def points(self, side: str) -> list[tuple[int, int]]:
        return self.left_points if side == "left" else self.right_points

    def clear_side(self, side: str) -> None:
        self.points(side).clear()

    def road_mask(self, shape: tuple[int, int, int]) -> np.ndarray:
        h, w = shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        if len(self.left_points) < 2 or len(self.right_points) < 2:
            return mask
        # Far-to-near ordering makes the polygon independent of whether the
        # annotator drew each curve upward or downward.
        left = sorted(self.left_points, key=lambda point: point[1])
        right = sorted(self.right_points, key=lambda point: point[1])
        polygon = np.asarray([*left, *reversed(right)], dtype=np.int32)
        cv2.fillPoly(mask, [polygon], 255)
        return mask

    def lane_mask(self, shape: tuple[int, int, int], thickness: int) -> np.ndarray:
        h, w = shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        for points in (self.left_points, self.right_points):
            if len(points) >= 2:
                cv2.polylines(mask, [np.asarray(points, dtype=np.int32)], False, 255, thickness, cv2.LINE_AA)
        return mask


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactively trace the two ego-lane markings and save masks consumable by the lane pipeline."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", default="T01-Sample")
    parser.add_argument("--frame", type=int, default=300)
    parser.add_argument("--step", type=int, default=1, help="Frame increment for [ and ].")
    parser.add_argument("--brush-px", type=int, default=7)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/training/roadface/manual_lane_masks"),
        help="Creates <trip>/lane_masks, <trip>/road_masks, and <trip>/metadata.",
    )
    return parser.parse_args()


def frame_path(trip_dir: Path, frame: int) -> Path | None:
    return find_image(trip_dir / "kitti" / "image_2", f"{frame:06d}")


def load_annotation(metadata_path: Path) -> Annotation:
    if not metadata_path.exists():
        return Annotation()
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    return Annotation(
        left_points=[tuple(map(int, point)) for point in data.get("left_points", [])],
        right_points=[tuple(map(int, point)) for point in data.get("right_points", [])],
    )


def draw_frame(
    image: np.ndarray,
    annotation: Annotation,
    side: str,
    brush_px: int,
    frame: int,
    cursor: tuple[int, int] | None,
) -> np.ndarray:
    canvas = image.copy()
    road_mask = annotation.road_mask(image.shape)
    if np.any(road_mask):
        tint = np.zeros_like(canvas)
        tint[:, :, 0] = 210
        tint[:, :, 1] = 180
        canvas = np.where(road_mask[:, :, None] > 0, cv2.addWeighted(canvas, 0.70, tint, 0.30, 0), canvas)
    for points, color in ((annotation.left_points, LEFT_COLOR), (annotation.right_points, RIGHT_COLOR)):
        if len(points) >= 2:
            cv2.polylines(canvas, [np.asarray(points, dtype=np.int32)], False, color, brush_px, cv2.LINE_AA)
        for point in points:
            cv2.circle(canvas, point, max(2, brush_px // 2), color, -1, cv2.LINE_AA)
    active_points = annotation.points(side)
    if cursor is not None and active_points:
        color = LEFT_COLOR if side == "left" else RIGHT_COLOR
        cv2.line(canvas, active_points[-1], cursor, color, 1, cv2.LINE_AA)
        cv2.circle(canvas, cursor, max(2, brush_px // 2), color, 1, cv2.LINE_AA)
    active = "LEFT" if side == "left" else "RIGHT"
    cv2.rectangle(canvas, (8, 8), (570, 88), (20, 25, 30), -1)
    cv2.putText(canvas, f"frame {frame:06d} | active boundary: {active} | brush {brush_px}px", (18, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (245, 245, 245), 1, cv2.LINE_AA)
    cv2.putText(canvas, "LMB: add point | RMB/Z: remove point | 1/2: left/right | C: clear side | S: save | [/]: frame | Q: quit", (18, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1, cv2.LINE_AA)
    return canvas


def save_annotation(base_dir: Path, trip: str, frame: int, annotation: Annotation, image: np.ndarray, brush_px: int) -> None:
    trip_dir = base_dir / trip
    lane_dir = trip_dir / "lane_masks"
    road_dir = trip_dir / "road_masks"
    meta_dir = trip_dir / "metadata"
    for directory in (lane_dir, road_dir, meta_dir):
        directory.mkdir(parents=True, exist_ok=True)
    stem = f"{frame:06d}"
    cv2.imwrite(str(lane_dir / f"{stem}.png"), annotation.lane_mask(image.shape, brush_px))
    cv2.imwrite(str(road_dir / f"{stem}.png"), annotation.road_mask(image.shape))
    (meta_dir / f"{stem}.json").write_text(
        json.dumps(
            {
                "frame": frame,
                "image_size": {"width": int(image.shape[1]), "height": int(image.shape[0])},
                "left_points": annotation.left_points,
                "right_points": annotation.right_points,
                "brush_px": brush_px,
                "format": "FleetIQ manual lane annotation v1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    frame = args.frame
    side = "left"
    brush_px = max(3, args.brush_px | 1)
    cursor: tuple[int, int] | None = None
    annotation = Annotation()
    image: np.ndarray | None = None

    def load_frame(target_frame: int) -> bool:
        nonlocal frame, annotation, image
        path = frame_path(trip_dir, target_frame)
        if path is None:
            print(f"No image for frame {target_frame:06d}")
            return False
        loaded = read_image(path)
        if loaded is None:
            print(f"Could not load {path}")
            return False
        frame = target_frame
        image = loaded
        metadata = args.output_dir / trip_dir.name / "metadata" / f"{frame:06d}.json"
        annotation = load_annotation(metadata)
        print(f"Loaded {trip_dir.name} frame {frame:06d}")
        return True

    if not load_frame(frame):
        raise SystemExit(2)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)

    def on_mouse(event: int, x: int, y: int, _flags: int, _param: object) -> None:
        nonlocal cursor
        if image is None:
            return
        cursor = (x, y)
        points = annotation.points(side)
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()

    cv2.setMouseCallback(WINDOW_NAME, on_mouse)
    while True:
        assert image is not None
        cv2.imshow(WINDOW_NAME, draw_frame(image, annotation, side, brush_px, frame, cursor))
        key = cv2.waitKey(20) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("1"):
            side = "left"
        elif key == ord("2"):
            side = "right"
        elif key in (ord("z"), 8):
            points = annotation.points(side)
            if points:
                points.pop()
        elif key == ord("c"):
            annotation.clear_side(side)
        elif key == ord("s"):
            save_annotation(args.output_dir, trip_dir.name, frame, annotation, image, brush_px)
            print(f"Saved {trip_dir.name} frame {frame:06d}")
        elif key == ord("["):
            load_frame(max(0, frame - args.step))
        elif key == ord("]"):
            load_frame(frame + args.step)
        elif key in (ord("-"), ord("_")):
            brush_px = max(3, brush_px - 2)
        elif key in (ord("+"), ord("=")):
            brush_px = min(31, brush_px + 2)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
