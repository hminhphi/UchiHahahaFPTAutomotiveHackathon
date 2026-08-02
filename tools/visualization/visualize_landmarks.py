"""Real-Time Driver & Road Facial Landmark Explorer (OpenCV GUI)
==================================================================
Ứng dụng trực quan hóa 468 MediaPipe Facial Landmarks thời gian thực,
camera hành trình đường đi (Road View), và SO SÁNH GIỮA GROUND TRUTH vs PREDICT LABEL (Bi-LSTM).

Chạy:
    uv run --package fleetiq-training-dms python tools/visualization/visualize_landmarks.py
    uv run --package fleetiq-training-dms python tools/visualization/visualize_landmarks.py --trip T01-Sample

Điều khiển phím tắt trong cửa sổ OpenCV:
    - SPACE: Phát / Tạm dừng Video (Play/Pause)
    - A / D hoặc Phím mũi tên Trái/Phải: Tua lùi / Tua tới 1 frame
    - W / S hoặc Phím mũi tên Lên/Xuống: Tăng / Giảm tốc độ FPS (FPS Speed)
    - N / P: Chuyển nhanh sang Trip Tiếp theo (Next) / Trip Trước đó (Prev)
    - ESC / Q: Thoát ứng dụng
"""

import argparse
import gzip
import json
from pathlib import Path
import sys
import cv2
import numpy as np
import pandas as pd

import torch
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Import mô hình suy luận từ Solution 2 (Two-Stage Bi-LSTM)
try:
    from fleetiq_training_dms.config import Config as Sol2Config
    from fleetiq_training_dms.model import build_sequence_model
    from fleetiq_training_dms.predict import predict_sequence_trip
    HAS_SOL2 = True
except Exception:
    HAS_SOL2 = False

# -----------------------------------------------------------------------------
# LANDMARK INDICES
# -----------------------------------------------------------------------------
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH = [13, 14, 78, 308]
PNP_6P = [1, 152, 33, 263, 61, 291]

MODEL_PATH = Path("artifacts/models/dms/face_landmarker.task")


def calculate_ear(pts: np.ndarray) -> float:
    """Tính Eye Aspect Ratio (EAR)."""
    p1, p2, p3, p4, p5, p6 = pts
    v1 = np.linalg.norm(p2 - p6)
    v2 = np.linalg.norm(p3 - p5)
    h = np.linalg.norm(p1 - p4)
    return float((v1 + v2) / (2.0 * h)) if h > 0 else 0.25


def calculate_mar(pts: np.ndarray) -> float:
    """Tính Mouth Aspect Ratio (MAR)."""
    p_top, p_bot, p_left, p_right = pts
    v = np.linalg.norm(p_top - p_bot)
    h = np.linalg.norm(p_left - p_right)
    return float(v / h) if h > 0 else 0.2


def estimate_head_pose(pts_6p: np.ndarray, img_w: int, img_h: int):
    """Ước lượng Head Pose 3D (Pitch, Yaw, Roll) dùng SolvePnP."""
    model_pts = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # L Eye
        (225.0, 170.0, -135.0),      # R Eye
        (-150.0, -150.0, -125.0),    # L Mouth
        (150.0, -150.0, -125.0)      # R Mouth
    ], dtype=np.float64)

    image_points = np.ascontiguousarray(pts_6p, dtype=np.float64)
    cam_mat = np.array([[img_w, 0, img_w / 2], [0, img_w, img_h / 2], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros((4, 1))

    success, rvec, tvec = cv2.solvePnP(model_pts, image_points, cam_mat, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not success:
        p0 = (int(pts_6p[0][0]), int(pts_6p[0][1]))
        return 0.0, 0.0, 0.0, p0, p0

    rmat, _ = cv2.Rodrigues(rvec)
    proj_mat = cv2.hconcat((rmat, tvec))
    _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(proj_mat)
    pitch, yaw, roll = euler[0][0], euler[1][0], euler[2][0]

    nose_end_point2D, _ = cv2.projectPoints(np.array([(0.0, 0.0, 500.0)]), rvec, tvec, cam_mat, dist)
    p1 = (int(pts_6p[0][0]), int(pts_6p[0][1]))
    p2 = (int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))

    return float(pitch), float(yaw), float(roll), p1, p2


def init_landmarker():
    """Khởi tạo MediaPipe FaceLandmarker Task API."""
    if not MODEL_PATH.exists():
        import urllib.request
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        print("[Info] Downloading face_landmarker.task model...")
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


def annotate_driver_frame(image_bgr: np.ndarray, landmarker, gt_state=None, pred_state=None) -> np.ndarray:
    """Trích xuất và vẽ 468 MediaPipe Facial Landmarks + Đối chiếu GT State vs Pred State."""
    h, w, _ = image_bgr.shape
    annotated = image_bgr.copy()

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
    res = landmarker.detect(mp_img)

    if res.face_landmarks and len(res.face_landmarks) > 0:
        lm = res.face_landmarks[0]
        coords = np.array([(int(p.x * w), int(p.y * h)) for p in lm])

        # 1. Vẽ 468 điểm mặt (Cyan nhạt)
        for pt in coords[::3]:
            cv2.circle(annotated, (pt[0], pt[1]), 1, (255, 255, 0), -1)

        # 2. Vẽ viền Mắt Trái & Mắt Phải (Xanh lá) & Tính EAR
        l_eye_pts = coords[LEFT_EYE]
        r_eye_pts = coords[RIGHT_EYE]
        cv2.polylines(annotated, [l_eye_pts], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.polylines(annotated, [r_eye_pts], isClosed=True, color=(0, 255, 0), thickness=2)
        ear_avg = (calculate_ear(l_eye_pts) + calculate_ear(r_eye_pts)) / 2.0

        # 3. Vẽ viền Miệng (Magenta) & Tính MAR
        mouth_pts = coords[MOUTH]
        cv2.polylines(annotated, [mouth_pts], isClosed=True, color=(255, 0, 255), thickness=2)
        mar = calculate_mar(mouth_pts)

        # 4. Hướng đầu 3D SolvePnP (Mũi tên đỏ)
        pnp_pts = coords[PNP_6P]
        pitch, yaw, roll, p1, p2 = estimate_head_pose(pnp_pts, w, h)
        cv2.arrowedLine(annotated, p1, p2, (0, 0, 255), 3, tipLength=0.3)

        eye_status = "CLOSED" if ear_avg < 0.18 else ("PARTIAL" if ear_avg <= 0.25 else "OPEN")
        mouth_status = "YAWNING" if mar > 0.55 else "NORMAL"
        head_status = "DOWN" if pitch < -12 else ("SIDE" if abs(yaw) > 15 else "NORMAL")

        cv2.putText(annotated, f"EAR: {ear_avg:.2f} ({eye_status})", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated, f"MAR: {mar:.2f} ({mouth_status})", (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        cv2.putText(annotated, f"Head: P={pitch:.1f}d, Y={yaw:.1f}d, R={roll:.1f}d ({head_status})", (15, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
    else:
        cv2.putText(annotated, "NO FACE DETECTED", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # 5. HIỂN THỊ ĐỐI CHIẾU NHÃN GROUND TRUTH vs PREDICT LABEL
    box_x = w - 340
    overlay = annotated.copy()
    cv2.rectangle(overlay, (box_x, 10), (w - 10, 110), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, annotated, 0.35, 0, annotated)
    cv2.rectangle(annotated, (box_x, 10), (w - 10, 110), (255, 255, 255), 1)

    if gt_state and gt_state != "N/A":
        gt_str = f"GT State:   {gt_state.upper()}"
        gt_color = (0, 255, 255)
    else:
        gt_str = "GT State:   N/A (Redacted)"
        gt_color = (150, 150, 150)
    cv2.putText(annotated, gt_str, (box_x + 10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, gt_color, 2)

    pred_str = f"Pred State: {pred_state.upper() if pred_state else 'N/A'}"
    cv2.putText(annotated, pred_str, (box_x + 10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 255), 2)

    if gt_state and gt_state != "N/A" and pred_state:
        if gt_state.lower() == pred_state.lower():
            status_text = "[ MATCH ✓ ]"
            status_color = (0, 255, 0)
        else:
            status_text = "[ MISMATCH ✗ ]"
            status_color = (0, 0, 255)
    elif pred_state:
        status_text = "[ PREDICTION MODE ]"
        status_color = (255, 200, 0)
    else:
        status_text = "[ NO PREDICTION ]"
        status_color = (128, 128, 128)

    cv2.putText(annotated, status_text, (box_x + 10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    return annotated


def discover_all_trips(root: Path):
    """Tìm tất cả các Trip trong data/Practice_Dataset và data/Hackathon_Dataset_Redacted."""
    trips = []
    search_dirs = [
        root / "data" / "Practice_Dataset" / "Practice_Dataset",
        root / "data" / "Hackathon_Dataset_Redacted" / "Hackathon_Dataset_Redacted",
    ]
    for d in search_dirs:
        if d.exists():
            for p in sorted(d.iterdir()):
                if p.is_dir() and (p / "driver").exists():
                    trips.append((p.name, p))
    return trips


def load_gt_states_from_json(trip_path: Path):
    """Đọc nhãn Ground Truth driver state từ file annotation JSON của trip."""
    trip_id = trip_path.name
    json_gz = trip_path / f"{trip_id}.json.gz"
    json_raw = trip_path / f"{trip_id}.json"

    frames_meta = []
    if json_gz.exists():
        with gzip.open(json_gz, "rt", encoding="utf-8") as f:
            data = json.load(f)
            frames_meta = data.get("frames", [])
    elif json_raw.exists():
        with open(json_raw, "r", encoding="utf-8") as f:
            data = json.load(f)
            frames_meta = data.get("frames", [])

    gt_dict = {}
    for fr in frames_meta:
        fid = fr.get("frame_id")
        st = fr.get("driver", {}).get("state", "N/A")
        gt_dict[fid] = st if st else "N/A"

    return gt_dict


def load_or_run_predictions(trip_path: Path, model=None, mean_scaler=None, std_scaler=None):
    """Tải hoặc chạy dự đoán mô hình Bi-LSTM cho trip."""
    trip_id = trip_path.name
    pred_dir = Path("artifacts/predictions/dms")

    candidates = [
        pred_dir / f"{trip_id}_predictions.csv",
        pred_dir / f"{trip_id}_twostage.csv",
        pred_dir / f"{trip_id}.csv",
    ]
    for pred_csv in candidates:
        if pred_csv.exists():
            df_pred = pd.read_csv(pred_csv)
            col_name = "predicted_driver_state" if "predicted_driver_state" in df_pred.columns else df_pred.columns[-1]
            return dict(zip(df_pred["frame_id"].astype(int), df_pred[col_name]))

    if HAS_SOL2 and model is not None:
        try:
            df_pred = predict_sequence_trip(
                model, trip_path, seq_len=Sol2Config.SEQ_LEN,
                mean_scaler=mean_scaler, std_scaler=std_scaler, device=Sol2Config.DEVICE
            )
            return dict(zip(df_pred["frame_id"], df_pred["predicted_driver_state"]))
        except Exception as e:
            print(f"[Warning] Prediction failed for {trip_id}: {e}")

    return {}


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Real-Time Driver & Road Landmark Explorer with GT vs Pred")
    parser.add_argument("--trip", type=str, default="", help="Trip name (e.g. T01-Sample or T01d)")
    args = parser.parse_args()

    root = Path.cwd()
    all_trips = discover_all_trips(root)

    if not all_trips:
        print("[Error] Không tìm thấy dữ liệu Trip nào trong data/Practice_Dataset hoặc data/Hackathon_Dataset_Redacted")
        return

    trip_idx = 0
    if args.trip:
        for idx, (t_name, t_path) in enumerate(all_trips):
            if args.trip.lower() in t_name.lower():
                trip_idx = idx
                break

    landmarker = init_landmarker()

    sol2_model = None
    mean_scaler = None
    std_scaler = None

    if HAS_SOL2:
        ckpt_path = Sol2Config.OUTPUT_DIR / "best_sequence_model.pt"
        if ckpt_path.exists():
            try:
                sol2_model = build_sequence_model(
                    feature_dim=18,
                    hidden_dim=Sol2Config.HIDDEN_DIM,
                    num_layers=Sol2Config.NUM_LAYERS,
                    num_classes=Sol2Config.NUM_CLASSES,
                    cell_type=Sol2Config.MODEL_TYPE
                ).to(Sol2Config.DEVICE)
                ckpt = torch.load(ckpt_path, map_location=Sol2Config.DEVICE, weights_only=False)
                sol2_model.load_state_dict(ckpt["model_state_dict"])
                sol2_model.eval()
                mean_scaler = ckpt.get("mean_scaler", None)
                std_scaler = ckpt.get("std_scaler", None)
            except Exception as e:
                print(f"[Warning] Cannot load Bi-LSTM model: {e}")

    win_name = "FPT Automotive Hackathon 2026 — Driver Landmark & GT vs Pred Visualizer"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 640)

    playing = False
    fps_delay_ms = 40
    current_frame = 0

    TRIP_CACHE = {}

    def load_trip_data(idx):
        t_name, t_path = all_trips[idx]
        if t_name in TRIP_CACHE:
            return TRIP_CACHE[t_name]

        driver_dir = t_path / "driver"
        driver_imgs = sorted(list(driver_dir.glob("*.jpg"))) if driver_dir.exists() else []

        road_dir = t_path / "kitti" / "image_2"
        if not road_dir.exists():
            road_dir = t_path / "kitti" / "image_02"

        gt_states = load_gt_states_from_json(t_path)
        pred_states = load_or_run_predictions(t_path, model=sol2_model, mean_scaler=mean_scaler, std_scaler=std_scaler)

        res = (t_name, t_path, driver_imgs, road_dir, gt_states, pred_states)
        TRIP_CACHE[t_name] = res
        return res

    trip_name, trip_path, driver_files, road_dir, gt_states, pred_states = load_trip_data(trip_idx)

    print(f"=== Đang mở Trip [{trip_name}] ({len(driver_files)} frames) ===")
    print(" [SPACE] Play/Pause | [A/D] Frame Prev/Next | [W/S] Speed +/- | [N/P] Trip Next/Prev | [ESC] Exit")

    while True:
        if not driver_files:
            print(f"[Warn] Trip {trip_name} không có ảnh driver!")
            break

        current_frame = max(0, min(current_frame, len(driver_files) - 1))
        d_img_path = driver_files[current_frame]
        driver_bgr = cv2.imread(str(d_img_path))

        if driver_bgr is not None:
            gt_st = gt_states.get(current_frame, "N/A")
            pred_st = pred_states.get(current_frame, None)

            annotated_driver = annotate_driver_frame(driver_bgr, landmarker, gt_state=gt_st, pred_state=pred_st)
            dh, dw, _ = annotated_driver.shape

            road_img_name = f"{current_frame:06d}.jpg"
            road_img_path = road_dir / road_img_name if road_dir.exists() else None

            if road_img_path and road_img_path.exists():
                road_bgr = cv2.imread(str(road_img_path))
                if road_bgr is not None:
                    rh, rw, _ = road_bgr.shape
                    new_rw = int(rw * (dh / rh))
                    road_resized = cv2.resize(road_bgr, (new_rw, dh))
                    cv2.putText(road_resized, f"ROAD CAMERA (Frame {current_frame})", (15, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                    canvas = cv2.hconcat([road_resized, annotated_driver])
                else:
                    canvas = annotated_driver
            else:
                canvas = annotated_driver

            status_str = "▶ PLAYING" if playing else "⏸ PAUSED"
            hud_text = f"[{status_str}] Trip: {trip_name} ({trip_idx+1}/{len(all_trips)}) | Frame {current_frame+1}/{len(driver_files)} | Speed: {1000//fps_delay_ms} FPS"
            cv2.putText(canvas, hud_text, (20, canvas.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.imshow(win_name, canvas)

        wait_time = fps_delay_ms if playing else 0
        key = cv2.waitKey(wait_time) & 0xFF

        if key == 27 or key == ord('q'):
            break
        elif key == 32:
            playing = not playing
        elif key == ord('a') or key == 81:
            current_frame = max(0, current_frame - 1)
            playing = False
        elif key == ord('d') or key == 83:
            current_frame = min(len(driver_files) - 1, current_frame + 1)
            playing = False
        elif key == ord('w') or key == 82:
            fps_delay_ms = max(10, fps_delay_ms - 10)
        elif key == ord('s') or key == 84:
            fps_delay_ms = min(200, fps_delay_ms + 10)
        elif key == ord('n'):
            trip_idx = (trip_idx + 1) % len(all_trips)
            trip_name, trip_path, driver_files, road_dir, gt_states, pred_states = load_trip_data(trip_idx)
            current_frame = 0
            print(f"-> Chuyển sang Trip [{trip_name}]")
        elif key == ord('p'):
            trip_idx = (trip_idx - 1 + len(all_trips)) % len(all_trips)
            trip_name, trip_path, driver_files, road_dir, gt_states, pred_states = load_trip_data(trip_idx)
            current_frame = 0
            print(f"-> Chuyển sang Trip [{trip_name}]")

        if playing:
            current_frame += 1
            if current_frame >= len(driver_files):
                current_frame = 0

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
