"""Prepare Vicomtech DMD face videos for FleetIQ DMS training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd

from fleetiq_training_dms.config import Config
from fleetiq_training_dms.feature_extractor import (
    calculate_ear,
    calculate_mar,
    estimate_head_pose_pnp,
    init_landmarker,
)


def label_for_action(action_type: str, annotation_path: Path, frames: int, fps: float) -> str | None:
    """Map Vicomtech OpenLABEL action types to FleetIQ training states."""
    action = action_type.casefold()
    if "yawn" in action:
        return "yawning"
    if "eyes_state/close" in action:
        return "microsleep" if frames >= fps else "drowsy" if frames >= fps / 2 else None
    if "distraction" in annotation_path.name.casefold() or any(
        word in action for word in ("phone", "mobile", "text", "call", "smok", "drink", "eat")
    ):
        return "distracted"
    return None


def labels_from_openlabel(annotation_path: Path, frame_count: int, fps: float) -> np.ndarray:
    """Return one FleetIQ state label per video frame from OpenLABEL intervals."""
    data = json.loads(annotation_path.read_text(encoding="utf-8"))
    actions = data.get("openlabel", {}).get("actions", {})
    labels = np.full(frame_count, Config.STATE_MAP["alert"], dtype=np.int64)

    for action in actions.values():
        intervals = action.get("frame_intervals", [])
        for interval in intervals:
            start = max(0, int(interval["frame_start"]))
            end = min(frame_count - 1, int(interval["frame_end"]))
            state = label_for_action(action.get("type", ""), annotation_path, end - start + 1, fps)
            if state:
                labels[start : end + 1] = max(labels[start : end + 1].max(), Config.STATE_MAP[state])
    return labels


def matching_annotation(video_path: Path) -> Path | None:
    prefix = video_path.name.removesuffix("_rgb_face.mp4")
    return next(iter(video_path.parent.glob(f"{prefix}_rgb_ann_*.json")), None)


def video_features(video_path: Path, labels: np.ndarray, landmarker) -> pd.DataFrame:
    """Extract FleetIQ's existing 18 features directly from a face video."""
    capture = cv2.VideoCapture(str(video_path))
    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    rows, previous_gray = [], None
    last = [0.28, 0.20, 0.0, 0.0, 0.0]
    frame_id = 0

    while frame_id < len(labels):
        ok, image_bgr = capture.read()
        if not ok:
            break
        height, width = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        motion = cv2.absdiff(gray, previous_gray) if previous_gray is not None else None
        previous_gray = gray
        ear, mar, pitch, yaw, roll = last

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb))
        if result.face_landmarks:
            coords = np.array([(point.x * width, point.y * height) for point in result.face_landmarks[0]])
            ear = (calculate_ear(coords[[33, 160, 158, 133, 153, 144]]) + calculate_ear(coords[[362, 385, 387, 263, 373, 380]])) / 2
            mar = calculate_mar(coords[[13, 14, 78, 308]])
            pitch, yaw, roll = estimate_head_pose_pnp(coords[[1, 152, 33, 263, 61, 291]], width, height)
            last = [ear, mar, pitch, yaw, roll]

        rows.append({
            "frame_id": frame_id,
            "timestamp": frame_id / fps,
            "ear": ear,
            "mar": mar,
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "brightness": float(gray.mean()) / 255,
            "motion_mean": float(motion.mean()) / 255 if motion is not None else 0.0,
            "motion_std": float(motion.std()) / 255 if motion is not None else 0.0,
            "state_label": int(labels[frame_id]),
        })
        frame_id += 1
    capture.release()

    df = pd.DataFrame(rows)
    for name in ("ear", "mar", "pitch", "yaw", "roll"):
        df[f"delta_{name}"] = df[name].diff().fillna(0.0)
    df["ear_mean_5"] = df["ear"].rolling(5, min_periods=1).mean()
    df["ear_std_5"] = df["ear"].rolling(5, min_periods=1).std().fillna(0.0)
    for name in ("mar", "pitch", "yaw"):
        df[f"{name}_mean_5"] = df[name].rolling(5, min_periods=1).mean()
    return df


def prepare(data_root: Path, output_dir: Path) -> int:
    """Prepare every labelled face video below data_root."""
    output_dir.mkdir(parents=True, exist_ok=True)
    landmarker = init_landmarker()
    prepared = 0
    for video_path in sorted(data_root.rglob("*_rgb_face.mp4")):
        annotation_path = matching_annotation(video_path)
        if annotation_path is None:
            print(f"[skip] no annotation for {video_path}")
            continue
        capture = cv2.VideoCapture(str(video_path))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        capture.release()
        if frame_count == 0:
            print(f"[skip] unreadable {video_path}")
            continue
        sample_id = video_path.name.removesuffix("_rgb_face.mp4")
        df = video_features(video_path, labels_from_openlabel(annotation_path, frame_count, fps), landmarker)
        df.insert(0, "trip_id", sample_id)
        output_path = output_dir / f"{sample_id}_features.csv"
        df.to_csv(output_path, index=False)
        prepared += 1
        print(f"[prepared] {sample_id}: {len(df)} frames -> {output_path}")
    return prepared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare Vicomtech DMD face videos for FleetIQ DMS training.")
    parser.add_argument("--data-root", type=Path, required=True, help="Root containing drowsiness/ and distraction/.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Config.REPO_ROOT / "artifacts" / "training" / "dms" / "vicomtech_features",
    )
    args = parser.parse_args(argv)
    if not args.data_root.is_dir():
        parser.error(f"Data root does not exist: {args.data_root}")
    return 0 if prepare(args.data_root, args.output_dir) else 1


if __name__ == "__main__":
    raise SystemExit(main())
