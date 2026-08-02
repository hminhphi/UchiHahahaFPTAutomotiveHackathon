# 📄 Technical Report: Solution 2 (Two-Stage Hybrid Bi-LSTM DMS)

## 📌 1. Kiến Trúc Giải Pháp (Architecture Overview)

Bài toán **Driver Intelligence Platform (Challenge 2)** phân loại 5 trạng thái tài xế (`alert`, `distracted`, `drowsy`, `microsleep`, `yawning`).

**Solution 2** sử dụng kiến trúc **Two-Stage Hybrid (Bi-LSTM)** kết hợp quan sát chuỗi thời gian:

```mermaid
graph TD
    A[Frame Ảnh Driver Raw / Video Stream] --> B[STAGE 1: Landmarker & Feature Extraction]
    B --> C["MediaPipe Face Mesh (468 3D Landmarks) + OpenCV SolvePnP"]
    C --> D["Vector Đặc Trưng Liên Tục (Pure Continuous Feature Vector D=18)"]
    D --> E[STAGE 2: Sliding Window Sequence Aggregation N=20 (~1.0s)]
    E --> F[2-Layer Bidirectional LSTM Model]
    F --> G[MLP Classifier Head + Softmax]
    G --> H["Trạng Thái Dự Đoán (5 Classes)"]
```

---

## 📊 2. Bảng 18 Features Sinh Học (Continuous Feature Breakdown)

| STT | Tên Feature | Nhóm | Mô Tả & Công Thức |
| :---: | :--- | :--- | :--- |
| 1 | `ear` | Hình học mắt | Eye Aspect Ratio $\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2 \|p_1 - p_4\|}$ |
| 2 | `mar` | Hình học miệng | Mouth Aspect Ratio $\text{MAR} = \frac{\|p_{\text{top}} - p_{\text{bottom}}\|}{\|p_{\text{left}} - p_{\text{right}}\|}$ |
| 3 | `pitch` | Hướng đầu 3D | Góc gật/cúi đầu từ OpenCV `solvePnP`. |
| 4 | `yaw` | Hướng đầu 3D | Góc xoay trái/phải từ `solvePnP`. |
| 5 | `roll` | Hướng đầu 3D | Góc nghiêng đầu sang vai từ `solvePnP`. |
| 6-10 | `delta_*` | Vận tốc | Tốc độ biến thiên thời gian $\Delta f_t = f_t - f_{t-1}$ cho EAR, MAR, Pitch, Yaw, Roll. |
| 11-15 | `*_mean_5`, `ear_std_5` | Thống kê trượt | Trung bình động & độ lệch chuẩn trong cửa sổ 5 frames. |
| 16 | `brightness` | Biến động ảnh | Độ sáng trung bình toàn khung hình (chuẩn hóa $0 \to 1$). |
| 17-18 | `motion_mean`, `motion_std` | Biến động chuyển động | Mức độ chuyển động pixel giữa 2 ảnh xám liên tiếp. |

---

## 🧠 3. Cấu Trúc Mô Hình (Model Architecture & Specs)

- **Input:** Tensor $[B, N, D] = [32, 20, 18]$
- **Backbone:** 2-Layer Bidirectional LSTM (`hidden_dim=128`, `bidirectional=True` $\to$ output $256$)
- **Sequence Pooling:** Last time-step hidden state output ($h_{\text{last}} \in \mathbb{R}^{B \times 256}$)
- **MLP Head:** `BatchNorm1d(256)` $\to$ `Dropout(0.2)` $\to$ `Linear(256, 128)` $\to$ `ReLU()` $\to$ `Linear(128, 5)`

---

## 📈 4. Kết Quả Huấn Luyện & Đánh Giá (Validation Results)

```text
               precision    recall  f1-score   support

        alert     0.9355    0.8700    0.9016       200
   distracted     0.7699    0.8700    0.8169       100
       drowsy     0.9901    1.0000    0.9950       100
   microsleep     1.0000    1.0000    1.0000       100
      yawning     1.0000    1.0000    1.0000       100

     accuracy                         0.9350       600
    macro avg     0.9391    0.9480    0.9427       600
 weighted avg     0.9385    0.9350    0.9358       600
```

- **Validation Accuracy:** **93.50%**
- **Macro F1-Score:** **0.9427**
- **Speed:** **> 500 FPS trên CPU**
- **Checkpoint size:** **~2.3 MB** tại `artifacts/models/dms/best_sequence_model.pt`

---

## 🛠 5. Hướng Dẫn Sử Dụng Trong Workspace

1. **Huấn luyện:**
   `uv run --package fleetiq-training-dms fleetiq-train-dms`
2. **Đánh giá:**
   `uv run --package fleetiq-training-dms fleetiq-evaluate-dms`
3. **Suy luận:**
   `uv run --package fleetiq-training-dms fleetiq-predict-dms --trip-dir data/Practice_Dataset/Practice_Dataset/T01-Sample`
4. **Trực quan hóa GUI (GUI Explorer & GT vs Pred):**
   `uv run --package fleetiq-training-dms python tools/visualization/visualize_landmarks.py --trip T01-Sample`
