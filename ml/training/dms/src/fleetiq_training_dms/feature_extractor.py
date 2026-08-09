"""MediaPipe & OpenCV 18-Feature Extractor for Driver Camera Frames."""

import gzip
import json
from pathlib import Path
import cv2
import numpy as np
import pandas as pd

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from fleetiq_training_dms.config import Config

# -----------------------------------------------------------------------------
# LANDMARK MEASUREMENT FUNCTIONS
# -----------------------------------------------------------------------------
def calculate_ear(eye_coords: np.ndarray) -> float:
    """Calculate Eye Aspect Ratio (EAR) from 6 landmark points."""
    p1, p2, p3, p4, p5, p6 = eye_coords
    vert1 = np.linalg.norm(p2 - p6)
    vert2 = np.linalg.norm(p3 - p5)
    horiz = np.linalg.norm(p1 - p4)
    if horiz == 0:
        return 0.25
    return float((vert1 + vert2) / (2.0 * horiz))


def calculate_mar(mouth_coords: np.ndarray) -> float:
    """Calculate Mouth Aspect Ratio (MAR) from 4 landmark points."""
    p_top, p_bottom, p_left, p_right = mouth_coords
    vert = np.linalg.norm(p_top - p_bottom)
    horiz = np.linalg.norm(p_left - p_right)
    if horiz == 0:
        return 0.2
    return float(vert / horiz)


def estimate_head_pose_pnp(landmarks_6p: np.ndarray, img_w: int, img_h: int) -> tuple[float, float, float]:
    """Estimate 3D head pose angles (Pitch, Yaw, Roll) using OpenCV solvePnP."""
    model_points = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left Eye
        (225.0, 170.0, -135.0),      # Right Eye
        (-150.0, -150.0, -125.0),    # Left Mouth Corner
        (150.0, -150.0, -125.0)      # Right Mouth Corner
    ], dtype=np.float64)

    image_points = np.array(landmarks_6p, dtype=np.float64)

    focal_length = float(img_w)
    center = (img_w / 2.0, img_h / 2.0)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))

    success, rotation_vec, translation_vec = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return 0.0, 0.0, 0.0

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    pose_mat = cv2.hconcat((rotation_mat, translation_vec))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)

    pitch, yaw, roll = euler_angles[0][0], euler_angles[1][0], euler_angles[2][0]
    return float(pitch), float(yaw), float(roll)


# -----------------------------------------------------------------------------
# MEDIAPIPE FACE LANDMARKER INITIALIZATION
# -----------------------------------------------------------------------------
MODEL_PATH = Config.OUTPUT_DIR / "face_landmarker.task"

def init_landmarker():
    """Initialize MediaPipe FaceLandmarker Task API."""
    if not MODEL_PATH.exists():
        import urllib.request
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"[Info] Downloading face_landmarker.task model to {MODEL_PATH}...")
        task_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        urllib.request.urlretrieve(task_url, MODEL_PATH)

    base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1
    )
    return vision.FaceLandmarker.create_from_options(options)


def extract_features_from_trip(trip_dir: str | Path, landmarker=None, is_train: bool = True) -> pd.DataFrame:
    """Extract 18 continuous features from driver camera frames in a trip directory."""
    trip_dir = Path(trip_dir)
    trip_id = trip_dir.name
    driver_dir = trip_dir / "driver"

    json_gz = trip_dir / f"{trip_id}.json.gz"
    json_raw = trip_dir / f"{trip_id}.json"

    frames_meta = []
    if json_gz.exists():
        with gzip.open(json_gz, "rt", encoding="utf-8") as f:
            data = json.load(f)
            frames_meta = data.get("frames", [])
    elif json_raw.exists():
        with open(json_raw, "r", encoding="utf-8") as f:
            data = json.load(f)
            frames_meta = data.get("frames", [])
    else:
        img_files = sorted(driver_dir.glob("*.jpg")) if driver_dir.exists() else []
        for idx, _ in enumerate(img_files):
            frames_meta.append({"frame_id": idx, "timestamp": idx * 0.05, "driver": {}})

    if landmarker is None:
        landmarker = init_landmarker()

    records = []
    prev_gray = None

    last_known_ear = 0.28
    last_known_mar = 0.20
    last_known_pitch = 0.0
    last_known_yaw = 0.0
    last_known_roll = 0.0

    for frame in frames_meta:
        frame_id = frame["frame_id"]
        timestamp = frame.get("timestamp", 0.0)
        driver_info = frame.get("driver", {})

        img_name = f"frame_{frame_id:06d}.jpg"
        img_path = driver_dir / img_name

        motion_mean = 0.0
        motion_std = 0.0
        brightness_mean = 0.0

        ear_val = last_known_ear
        mar_val = last_known_mar
        pitch_val = last_known_pitch
        yaw_val = last_known_yaw
        roll_val = last_known_roll

        if img_path.exists():
            image_bgr = cv2.imread(str(img_path))
            if image_bgr is not None:
                h, w, _ = image_bgr.shape
                gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
                brightness_mean = float(np.mean(gray)) / 255.0

                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    motion_mean = float(np.mean(diff)) / 255.0
                    motion_std = float(np.std(diff)) / 255.0

                prev_gray = gray

                image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
                res = landmarker.detect(mp_image)

                if res.face_landmarks and len(res.face_landmarks) > 0:
                    lm = res.face_landmarks[0]
                    coords = np.array([(p.x * w, p.y * h) for p in lm])

                    left_eye = coords[[33, 160, 158, 133, 153, 144]]
                    right_eye = coords[[362, 385, 387, 263, 373, 380]]
                    ear_val = (calculate_ear(left_eye) + calculate_ear(right_eye)) / 2.0

                    mouth = coords[[13, 14, 78, 308]]
                    mar_val = calculate_mar(mouth)

                    pnp_points = coords[[1, 152, 33, 263, 61, 291]]
                    pitch_val, yaw_val, roll_val = estimate_head_pose_pnp(pnp_points, w, h)

                    last_known_ear = ear_val
                    last_known_mar = mar_val
                    last_known_pitch = pitch_val
                    last_known_yaw = yaw_val
                    last_known_roll = roll_val

        state_str = driver_info.get("state")
        state_label = Config.STATE_MAP.get(state_str, -1)

        row = {
            "frame_id": frame_id,
            "timestamp": timestamp,
            "ear": ear_val,
            "mar": mar_val,
            "pitch": pitch_val,
            "yaw": yaw_val,
            "roll": roll_val,
            "brightness": brightness_mean,
            "motion_mean": motion_mean,
            "motion_std": motion_std,
            "state_label": state_label,
        }
        records.append(row)

    df = pd.DataFrame(records)

    # Time-series deltas
    df["delta_ear"] = df["ear"].diff().fillna(0.0)
    df["delta_mar"] = df["mar"].diff().fillna(0.0)
    df["delta_pitch"] = df["pitch"].diff().fillna(0.0)
    df["delta_yaw"] = df["yaw"].diff().fillna(0.0)
    df["delta_roll"] = df["roll"].diff().fillna(0.0)

    # Rolling statistics
    df["ear_mean_5"] = df["ear"].rolling(window=5, min_periods=1).mean()
    df["ear_std_5"] = df["ear"].rolling(window=5, min_periods=1).std().fillna(0.0)
    df["mar_mean_5"] = df["mar"].rolling(window=5, min_periods=1).mean()
    df["pitch_mean_5"] = df["pitch"].rolling(window=5, min_periods=1).mean()
    df["yaw_mean_5"] = df["yaw"].rolling(window=5, min_periods=1).mean()

    return df


def extract_all_and_save():
    """Extract features for all configured trips and save CSVs."""
    Config.FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    all_trips = Config.ALL_TRIPS
    print(f"[Stage 1] Extracting 18 Pure Continuous Features for trips: {all_trips}")

    landmarker = init_landmarker()

    for trip_id in all_trips:
        # Use get_trip_dir() to support both Practice_Dataset and DMD_Processed
        trip_dir = Config.get_trip_dir(trip_id)
        if not trip_dir.exists():
            print(f"[Warning] Trip dir {trip_dir} does not exist.")
            continue

        # Skip if already extracted
        save_path = Config.FEATURE_DIR / f"{trip_id}_features.csv"
        if save_path.exists():
            print(f"[Skip] {trip_id} features already extracted -> {save_path}")
            continue

        df = extract_features_from_trip(trip_dir, landmarker=landmarker, is_train=True)
        df.to_csv(save_path, index=False)
        print(f" -> Extracted {len(df)} rows for {trip_id} -> {save_path}")


if __name__ == "__main__":
    extract_all_and_save()
