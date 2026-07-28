# TCN & Knowledge Distillation - Core Algorithm Architecture

Tài liệu này mô tả chi tiết về khối Trí tuệ nhân tạo (AI Engine) đằng sau hệ thống **FleetIQ Guardian**, bao gồm lý thuyết về mô hình ModernTCN và bộ luật Teacher (Rule-based) được sử dụng để sinh Ground-Truth.

---

## 1. Tại sao lại là ModernTCN? (Vượt qua giới hạn của Transformer)

Trong bối cảnh hệ điều hành xe hơi (CarSky / Edge AI), năng lực xử lý (Compute) và bộ nhớ (RAM) là cực kỳ giới hạn. Các mô hình dựa trên Transformer (như Vision/Time-Series Transformer) tuy mạnh nhưng tiêu tốn tài nguyên khổng lồ do độ phức tạp của cơ chế Attention ($O(N^2)$).

Giải pháp đột phá của chúng tôi là áp dụng tư tưởng của **ModernTCN (Modern Temporal Convolutional Network)**:
- **Kế thừa kiến trúc hiện đại (Modernized CNN):** ModernTCN mượn các thiết kế tiên tiến từ ConvNeXt và Vision Transformers (như tách biệt Channel Mixing và Spatial Mixing thông qua Inverted Bottlenecks).
- **Large Kernel Depthwise Convolutions:** Sử dụng các bộ lọc (filters) tích chập với kích thước hạt nhân lớn (large kernel sizes) để mở rộng "tầm nhìn thời gian" (Receptive Field) mà không làm phình to lượng tham số.
- **Tối ưu hóa đa biến (Multivariate Time-Series):** Xử lý cực kỳ tốt chuỗi dữ liệu chứa nhiều biến số (như sự kết hợp giữa Tốc độ xe, Khoảng cách TTC, và Độ mở mắt của tài xế).
- **Kết luận:** ModernTCN chứng minh rằng: Một mạng CNN được hiện đại hóa có thể đạt được độ chính xác (State-of-the-Art) ngang ngửa hoặc hơn Transformer trong bài toán chuỗi thời gian, nhưng với tốc độ xử lý nhanh hơn gấp nhiều lần. Đây là mô hình sinh ra để dành cho Automotive Edge AI.

---

## 2. Chiến thuật Knowledge Distillation (Teacher - Student)

Thay vì cố gắng gán nhãn thủ công (Manual Labeling) hàng ngàn khung hình video, hệ thống áp dụng kỹ thuật Truyền đạt tri thức (Knowledge Distillation):
- **Teacher Model (Người thầy):** Là bộ luật Rule-based siêu khắt khe, phân tích logic đa cảm biến (Sensor Fusion) để chấm điểm chính xác từng khung hình.
- **Student Model (Học sinh):** Là mạng ModernTCN. Mô hình này "nhìn" vào 9 đặc trưng (features) của 30 khung hình gần nhất, và học cách dự đoán quỹ đạo điểm số do "Người thầy" tạo ra. Nhờ bản chất tích chập, TCN tự động "nội suy" và làm mượt (smooth) các góc gãy của luật if-else, tạo ra đồ thị Risk Score tự nhiên và chống báo động giả (False Alarms) tuyệt đối.

---

## 3. Bộ luật của Teacher Model (Fusion Engine Rules)

Điểm cơ sở ban đầu (Safe Score) là **100**. Hệ thống sẽ kiểm tra cửa sổ quá khứ (History Window) và trừ điểm dựa trên 5 khía cạnh cốt lõi:

### A. Driver State (Trạng thái Tài xế)
- **Điểm tập trung (Alertness Penalty):** `Phạt = (1.0 - Alertness_Score) * 25`. Lơ đãng càng nhiều, trừ càng nặng (Tối đa 25đ).
- **Trạng thái Mất tập trung:**
  - `distracted`: Trừ thẳng **15 điểm**.
  - `drowsy`: Trừ thẳng **25 điểm**.
- **Nhắm mắt ngủ gật (Micro-sleep) có lọc nhiễu:**
  - Đếm số frames nhắm mắt trong 10 frames gần nhất.
  - Nếu `> 3 frames` (~0.15s, loại bỏ chớp mắt sinh học tự nhiên): Trừ **15 điểm**.
- **Ngáp kéo dài (Prolonged Yawning):**
  - Nhìn vào lịch sử 10 frames:
  - Nếu ngáp liên tục `> 10 frames` (Nửa giây): Phạt cực nặng **35 điểm**.
  - Nếu ngáp `> 5 frames`: Phạt **20 điểm**.
  - Dưới 5 frames (Ngáp nhẹ): Phạt **10 điểm**.

### B. Collision Risk (Rủi ro Va chạm - Radar/Depth)
- Nếu Thời gian va chạm `TTC < 1.5s` và `Speed > 20 km/h`: Báo động khẩn cấp, trừ **35 điểm**.
- Nếu `1.5s <= TTC < 2.5s` và `Speed > 20 km/h`: Cảnh báo khoảng cách, trừ **15 điểm**.

### C. Compound Risk (Nhân đôi Rủi ro - Điểm ăn tiền của Fusion Engine)
Nếu các rủi ro xảy ra đồng thời, sự nguy hiểm không phép cộng, mà là phép nhân:
- **Tài xế lơ đãng + Bám sát xe trước:** Nếu `Alertness < 0.5` (Hoặc đang Distracted/Drowsy/Nhắm mắt) **VÀ** `TTC < 2.5s`.
- Phạt cộng dồn **20 điểm** (Do phản xạ phanh lúc này gần như bằng 0).

### D. Vehicle Handling (Điều khiển Xe - IMU)
- **Phanh gấp (Harsh Braking):** Gia tốc dọc `Longitudinal_Accel < -3.0 m/s²` -> Trừ **20 điểm**.
- **Đánh lái gắt (Harsh Steering):** Gia tốc ngang `|Lateral_Accel| > 3.0 m/s²` -> Trừ **15 điểm**.

### E. Lane Behavior (Hành vi lệch làn - Ground Truth)
- Sự kiện `lane_departure` kích hoạt: Trừ **15 điểm**.
- Lệch làn ở tốc độ cao (`Speed > 60 km/h`): Trừ thêm **10 điểm**.

---
*Tất cả các hình phạt trên được tổng hợp lại. Nếu `Safe Score < 50`, hệ thống lập tức gọi API gRPC lên **KUKSA Databroker** để kích hoạt hệ thống chuông cảnh báo haptic/audio trên xe.*
