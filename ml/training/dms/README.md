# FleetIQ DMS Training & Evaluation Workspace (Solution 2: Two-Stage Bi-LSTM)

Gói `fleetiq-training-dms` cung cấp môi trường huấn luyện, đánh giá và suy luận offline cho **Solution 2 (Two-Stage Hybrid Bi-LSTM Driver State Classification)**.

---

## 📌 Tổng Quan Kiến Trúc (Solution 2 Architecture)

Giải pháp phân loại 5 trạng thái tài xế (`alert`, `distracted`, `drowsy`, `microsleep`, `yawning`) thông qua hai giai đoạn:

1. **Stage 1 (Feature Extraction):** Trích xuất 18 đặc trưng liên tục tinh khiết (Pure Continuous Features $D=18$) per frame bằng MediaPipe Face Mesh (468 3D landmarks) & OpenCV `solvePnP`:
   - `ear`, `mar`, `pitch`, `yaw`, `roll`
   - Vận tốc biến thiên theo thời gian: `delta_ear`, `delta_mar`, `delta_pitch`, `delta_yaw`, `delta_roll`
   - Thống kê trượt (Rolling stats 5f): `ear_mean_5`, `ear_std_5`, `mar_mean_5`, `pitch_mean_5`, `yaw_mean_5`
   - Thuộc tính ảnh: `brightness`, `motion_mean`, `motion_std`
2. **Stage 2 (Sequential Time-Series Classification):** Gom chuỗi cửa sổ trượt $N=20$ frames liên tiếp (~1.0s) đưa qua mô hình **2-Layer Bidirectional LSTM (Bi-LSTM)** + MLP Head.

---

## 🚀 Hướng Dẫn Sử Dụng (Usage & Commands)

### 0. Download Vicomtech DMD data

Save the forwarded Vicomtech links as plain text (the signed URLs expire), then run:

```bash
uv run --package fleetiq-training-dms fleetiq-download-dms \
  --manifest /path/to/vicomtech-dms-links.txt
```

Add `--convert-to-json` to create a grouped `.json` manifest beside the text
file and download using that JSON.

The script extracts drowsiness data to `data/dmd/drowsiness/`, distraction data to
`data/dmd/distraction/`, and keeps archives under `data/dmd/.archives/`. Use
`--dataset drowsiness` or `--dataset distraction` to download only one group.
Use `--delete-archives` when disk space is limited.

### 0.1 Prepare face videos for training

Only `*_rgb_face.mp4` files are read; frames are streamed into the existing 18-feature CSV format.

```bash
uv run --package fleetiq-training-dms fleetiq-prepare-vicomtech-dms \
  --data-root data/DMD

uv run --package fleetiq-training-dms fleetiq-train-dms \
  --feature-dir artifacts/training/dms/vicomtech_features
```

### 1. Trích xuất đặc trưng & Huấn luyện mô hình (Training)

Chạy huấn luyện mô hình với chiến lược Temporal Block Split (80% past train / 20% future val):

```powershell
uv run --package fleetiq-training-dms fleetiq-train-dms
```

Trọng số tốt nhất và thông số Z-score scaler sẽ được tự động lưu tại:
`artifacts/models/dms/best_sequence_model.pt`

### 2. Đánh giá mô hình (Evaluation)

Chạy đánh giá Accuracy, Macro F1-Score, Classification Report và vẽ ma trận nhầm lẫn Confusion Matrix:

```powershell
uv run --package fleetiq-training-dms fleetiq-evaluate-dms
```

Biểu đồ ma trận nhầm lẫn sẽ được xuất tại:
`artifacts/models/dms/confusion_matrix.png`

### 3. Suy luận trên một Trip (Inference)

Chuẩn bị checkpoint YOLO một lần (có thể cần network), sau đó chạy dự đoán
theo khung hình cho một trip. DMS state vẫn là nhãn attention tổng quát;
`phone_use` là tín hiệu độc lập và có thể để trống khi detector unavailable
hoặc đang warm up.

```bash
uv run --with ultralytics python -c 'from ultralytics import YOLO; YOLO("yolo11n.pt")'
```

```bash
uv run --with ultralytics --package fleetiq-training-dms python -c 'from fleetiq_training_dms.predict import main; main()' --trip-dir data/Practice_Dataset/T01-Sample --phone-model yolo11n.pt --phone-confidence 0.40 --output artifacts/predictions/dms/T01-Sample_twostage.csv
```

The prediction artifact contains `frame_id`, `timestamp`,
`predicted_driver_state`, and `phone_use`. The API overlays this CSV when
`FLEETIQ_DMS_PREDICTION_ROOT=artifacts/predictions/dms` is configured.

For phone detection only, without running the DMS classifier:

```bash
uv run --with ultralytics --package fleetiq-training-dms \
  python tools/detect_phone_use.py \
  --trip-dir data/Practice_Dataset/T01-Sample
```

This updates `artifacts/predictions/dms/T01-Sample_twostage.csv`, which the
API and notebook can use directly.

For a live webcam, press `q` to stop:

```bash
uv run --with ultralytics --package fleetiq-training-dms \
  python tools/live_phone_use.py
```

Use `--camera 1` if the desired camera is not webcam index 0.

---

## 📊 Thống Kê Hiệu Năng (Validation Results)

- **Validation Accuracy:** **93.50%**
- **Macro F1-Score:** **0.9427**
- **Inference Speed:** **> 500 FPS trên CPU** (Không cần GPU)
- **Model Checkpoint Size:** **~2.3 MB**

Xem báo cáo kỹ thuật đầy đủ tại [docs/models/solution_2_twostage_dms.md](../../docs/models/solution_2_twostage_dms.md).
