# FleetIQ DMS Training & Evaluation Workspace (Solution 2: Two-Stage Bi-LSTM)

Gói `fleetiq-training-dms` cung cấp môi trường huấn luyện, đánh giá và suy luận offline cho **Solution 2 (Two-Stage Hybrid Bi-LSTM Driver State Classification)**.

---

## 📌 Tổng Quan Kiến Trúc (Solution 2 Architecture)

Giải pháp phân loại 5 trạng thái tài xế (`alert`, `distracted`, `drowsy`, `microsleep`, `yawning`) thông qua hai giai đoạn:

1. **Stage 1 (Feature Extraction):** Trích xuất 18 đặc trưng liên tục tinh khiết (Pure Continuous Features $D=18$) per frame bằng MediaPipe Face Mesh (468 3D landmarks) & OpenCV `solvePnP`:
   - `ear`, `mar`, `pitch`, `yaw`, `roll`
   - Vận tốc biến thiên theo thời gian: `delta_ear`, `delta_mar`, `delta_pitch`, `delta_yaw`, `delta_roll`
    - Thống kê trượt (Rolling stats 15f): `ear_mean_5`, `ear_std_5`, `mar_mean_5`, `pitch_mean_5`, `yaw_mean_5` (giữ tên schema cũ để tương thích checkpoint)
   - Thuộc tính ảnh: `brightness`, `motion_mean`, `motion_std`
2. **Stage 2 (Sequential Time-Series Classification):** Gom chuỗi cửa sổ trượt $N=20$ frames liên tiếp (~1.0s) đưa qua mô hình **2-Layer Bidirectional LSTM (Bi-LSTM)** + MLP Head.

---

## 🚀 Hướng Dẫn Sử Dụng (Usage & Commands)

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

## Runtime Disclosure

The final Round 2 dashboard does not run this checkpoint. Its DMS state stream is produced
by MediaPipe face geometry with 15-frame smoothing and consolidated event
windows. Treat any historical checkpoint evaluation result as a training
artifact, not a runtime metric or a redacted-trip accuracy claim.

Read [final model provenance](../../../docs/models/PROVENANCE_FINAL.md) and the
[technical feature reference](../../../docs/models/solution_2_twostage_dms.md)
before reporting a DMS metric.
