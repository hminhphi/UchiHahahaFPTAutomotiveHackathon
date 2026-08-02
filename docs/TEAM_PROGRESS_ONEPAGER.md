# BÁO CÁO TIẾN ĐỘ NHÓM UCHIHAHAHA

**Dự án:** FleetIQ Guardian - Driver Intelligence & Collision Risk Platform  
**Cuộc thi:** FPT Automotive Hackathon 2026 | **Cập nhật:** 27/07/2026  
**Nhân sự:** 5 thành viên (4 AI, 1 Automotive C++)

## Mục tiêu

FleetIQ Guardian kết hợp camera trước xe, camera trong cabin, depth, calibration và telemetry để phát hiện nguy cơ va chạm, đánh giá trạng thái tài xế và tạo cảnh báo có bằng chứng. Nhóm chọn **Challenge #3 - Driver Intelligence Platform**, với hai nhánh AI chính là **Road-facing Perception** và **Driver Status Detection**, sau đó hợp nhất thành Trip Score và dashboard cho Fleet Manager.

## Tiến độ theo workstream

| Workstream | Trạng thái | Kết quả hiện tại |
|---|---|---|
| **Dataset Analysis** | Nền tảng hoàn thành | Đã phân tích 6 trip Practice Dataset, tổng **3.600 frame**; đồng bộ `image_2`, `image_3`, depth, calibration, driver camera, label và telemetry. Đã có notebook thống kê và trình xem theo trip/frame. |
| **Road-facing Perception** | Đang hoàn thiện | Đã xây dựng pipeline detection/relabel, depth-based distance, tracking, relative speed, TTC và visualization. LocateAnything đã tạo `label2_custom` cho **3.600/3.600 frame** với 6 nhóm vật cản: car, bus, long vehicle, motorcycle, cyclist và pedestrian. |
| **Lane/Road Understanding** | Đang hiệu chỉnh | Đã thử road/lane mask, camera-ground-plane prior và công cụ gán lane thủ công. Lane thẳng tương đối ổn; lane cong, điểm bắt đầu lane và trường hợp bị che khuất vẫn cần cải thiện trước khi dùng để lọc vật cản trong ego-lane. |
| **Driver Status Detection** | Đang nghiên cứu | Thành viên phụ trách đang khảo sát mô hình cho `attentive`, `distracted`, `drowsy`, `unknown`; tín hiệu dự kiến gồm eye closure, head pose, gaze/phone use và temporal smoothing. Chưa chốt model và chưa có benchmark chung trên dataset. |
| **Fusion & Product Demo** | Có khung kiến trúc | Đã xác định event schema, logic TTC/risk và luồng dashboard. Chưa nối hoàn chỉnh Road-facing, Driver Status và telemetry thành compound event, trip score, evidence timeline và coaching recommendation. |

## Kết quả có thể trình diễn

- Trình xem đồng bộ hai camera trước, driver view, depth, calibration, telemetry và label.
- Custom bounding box cho toàn bộ Practice Dataset, không ghi đè label gốc.
- Pipeline thử nghiệm detection → tracking → distance → relative speed → TTC.
- Visualization lane/road, contact sheet kiểm tra chất lượng và video/frame overlay.
- Proposal deck, kiến trúc hệ thống, môi trường Python 3.12/`uv`; **7/7 automated tests đang pass**.

## Ưu tiên 2-3 tuần tiếp theo

1. **Chốt Road-facing baseline:** đánh giá custom label, ổn định tracking và TTC trên cả 6 trip; chỉ ưu tiên vật cản trong vùng di chuyển của ego vehicle.
2. **Chốt Driver Status MVP:** chọn model, chuẩn hóa bốn trạng thái đầu ra, confidence và timeline theo trip.
3. **Tích hợp Risk Fusion:** tạo sự kiện như “mất tập trung + TTC thấp”, kèm severity, confidence, timestamp và evidence.
4. **Hoàn thiện demo end-to-end:** dashboard một trip, video overlay, score breakdown, near-miss alert và coaching recommendation; sau đó kiểm thử đủ 6 trip.

## Rủi ro cần kiểm soát

- **Label/bbox chưa sạch:** dùng `label2_custom`, lưu raw response để audit và kiểm tra thủ công frame khó.
- **Lane cong hoặc bị che:** kết hợp road plane, bằng chứng một phía và temporal tracking; không nội suy khi thiếu bằng chứng.
- **Depth/TTC dao động:** lọc ngoại lai, median trong ROI, temporal smoothing và cảnh báo theo event window.
- **Driver Status chưa có benchmark:** ưu tiên pretrained model + rule fusion cho MVP, luôn cho phép output `unknown`.

> **Mốc tích hợp gần nhất:** hoàn thành một trip chạy xuyên suốt  
> **Road Risk + Driver Status + Telemetry → Compound Event → Trip Score → Evidence Dashboard**.


