from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from fleetiq_training_roadface.experimental import (
    CLASS_COLORS,
    detections_from_labels,
    draw_tag,
    find_image,
    parse_calibration,
    read_image,
    resolve_trip,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize KITTI bounding boxes from label_2 or label2_custom."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", required=True)
    parser.add_argument("--label-dir-name", default="label2_custom")
    parser.add_argument("--frame", type=int)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--mode", choices=("frame", "video", "window", "contact-sheet"), default="frame")
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def render_labels(image: np.ndarray, detections: list, caption: str) -> np.ndarray:
    output = image.copy()
    for index, det in enumerate(detections, start=1):
        color = CLASS_COLORS.get(det.object_type, (220, 220, 220))
        x1, y1, x2, y2 = [int(round(value)) for value in det.bbox]
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        draw_tag(output, f"{index} {det.object_type}", (x1, max(18, y1 - 4)), color)
    cv2.rectangle(output, (0, output.shape[0] - 28), (output.shape[1], output.shape[0]), (20, 25, 30), -1)
    cv2.putText(
        output,
        f"{caption} | objects={len(detections)}",
        (10, output.shape[0] - 9),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (240, 240, 240),
        1,
        cv2.LINE_AA,
    )
    return output


def frame_ids(trip_dir: Path, args: argparse.Namespace) -> list[int]:
    if args.frame is not None:
        return [args.frame]
    ids = sorted(
        int(path.stem)
        for path in (trip_dir / "kitti" / "image_2").iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stem.isdigit()
    )
    selected = [
        frame_id
        for frame_id in ids
        if frame_id >= args.start
        and (args.end is None or frame_id <= args.end)
        and (frame_id - args.start) % max(1, args.stride) == 0
    ]
    return selected[: args.max_frames] if args.max_frames is not None else selected


def render_frame(trip_dir: Path, label_dir_name: str, frame_id: int) -> np.ndarray | None:
    stem = f"{frame_id:06d}"
    image = read_image(find_image(trip_dir / "kitti" / "image_2", stem))
    if image is None:
        return None
    calibration = parse_calibration(trip_dir / "kitti" / "calib" / f"{stem}.txt")
    detections = detections_from_labels(
        trip_dir / "kitti" / label_dir_name / f"{stem}.txt",
        calibration,
        image.shape,
        source=label_dir_name,
    )
    return render_labels(image, detections, f"{trip_dir.name} frame {stem} | {label_dir_name}")


def contact_sheet(frames: list[np.ndarray], columns: int = 3) -> np.ndarray:
    if not frames:
        raise ValueError("No frames to render.")
    target_w = 640
    target_h = 360
    tiles = [cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA) for frame in frames]
    rows = (len(tiles) + columns - 1) // columns
    blank = np.full_like(tiles[0], 20)
    tiles.extend([blank] * (rows * columns - len(tiles)))
    return np.vstack([np.hstack(tiles[row * columns : (row + 1) * columns]) for row in range(rows)])


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    ids = frame_ids(trip_dir, args)
    if not ids:
        raise SystemExit("No selected frames.")
    default_suffix = ".mp4" if args.mode == "video" else ".png"
    output = args.output or (
        Path("artifacts/roadface/label_visualization")
        / f"{trip_dir.name}_{args.label_dir_name}_{args.mode}{default_suffix}"
    )
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered: list[np.ndarray] = []
    writer = None
    try:
        for frame_id in ids:
            frame = render_frame(trip_dir, args.label_dir_name, frame_id)
            if frame is None:
                continue
            if args.mode == "frame":
                cv2.imwrite(str(output.with_suffix(".png")), frame)
                print(f"Wrote {output.with_suffix('.png')}")
                return
            if args.mode == "contact-sheet":
                rendered.append(frame)
                continue
            if args.mode == "window":
                cv2.imshow("FleetIQ KITTI labels", frame)
                if (cv2.waitKey(max(1, int(1000 / args.fps))) & 0xFF) in (27, ord("q")):
                    break
                continue
            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(
                    str(output.with_suffix(".mp4")),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    args.fps,
                    (w, h),
                )
            writer.write(frame)
    finally:
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()
    if args.mode == "contact-sheet":
        cv2.imwrite(str(output.with_suffix(".png")), contact_sheet(rendered))
        print(f"Wrote {output.with_suffix('.png')}")
    elif args.mode == "video":
        print(f"Wrote {output.with_suffix('.mp4')}")


if __name__ == "__main__":
    main()
