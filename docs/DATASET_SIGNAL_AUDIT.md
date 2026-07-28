# Kiểm Tra Tín Hiệu Practice Dataset

**Ngày kiểm tra:** 28/07/2026  
**Phạm vi:** `data/Practice_Dataset/Practice_Dataset`, 6 trip từ `T01-Sample` đến `T06-Sample`

## 1. Độ phủ dữ liệu

Mỗi trip dài 30 giây ở 20 FPS, tương ứng 600 frame.

| Nguồn | Số mẫu/trip | Tần số | Ghi chú |
|---|---:|---:|---|
| `kitti/image_2` | 600 | 20 Hz | Camera trước bên trái, 640×360 |
| `kitti/image_3` | 600 | 20 Hz | Camera trước bên phải, 640×360 |
| `kitti/calib` | 600 | 20 Hz | Nội tại/ngoại tại lặp lại ở mọi frame |
| `kitti/label_2` | 600 | 20 Hz | KITTI labels do BTC cung cấp |
| `driver` | 600 | 20 Hz | Camera trong cabin |
| `frames` trong JSON | 600 | 20 Hz | Telemetry, target, DMS và risk ground truth |
| `kitti/depth` | 120 | 5 Hz | Một depth map mỗi 5 camera frame |

Tổng cộng Practice Dataset có 3.600 stereo pair, 3.600 driver frame, 3.600 telemetry frame và 720 depth ground-truth map.

## 2. Camera Calibration

Calibration giống nhau ở cả 600 frame và cả 6 trip:

```text
fx = 320 px
fy = 320 px
cx = 320 px
cy = 180 px
image = 640 x 360 px
P2[0,3] = 0
P3[0,3] = -96
baseline = |P3[0,3] / fx - P2[0,3] / fx| = 0.30 m
```

`R0_rect`, `Tr_velo_to_cam` và `Tr_imu_to_velo` đều là identity. Điều này cho thấy stereo pair đã được rectified và có baseline 30 cm, nhưng file calibration **không chứa IMU attitude động, camera height hoặc camera mounting pitch thực tế**. Không được gọi các ma trận identity này là dữ liệu IMU theo frame.

Các giá trị `ego.rotation.yaw/pitch/roll` trong JSON là nguồn attitude động phù hợp hơn. Khi tính horizon, dùng rotation này như IMU/vehicle attitude proxy, kết hợp với `K` từ `P2` và kiểm tra lại quy ước trục bằng road plane.

## 3. Các Trường Có Trong JSON

### Trip-Level

- `trip_id`
- `metadata`: CARLA version, map, duration, FPS, weather, driver profile, random seed, speed limit và mô tả scenario.
- `driver_summary`: subject, condition, alertness, fatigue, longest drowsy episode, microsleep và state distribution.
- `trip_aggregate`: headway, risk score, safe-driving score, near miss, harsh acceleration/brake/corner, speeding và tailgating.
- `events_log`: thời điểm, loại scenario và tham số tạo sự kiện.

### Frame-Level

- `frame_id`, `world_frame`, `timestamp`
- `ego.speed_kmh`
- `ego.longitudinal_accel`, `ego.lateral_accel`
- `ego.location.x/y/z`
- `ego.rotation.yaw/pitch/roll`
- `ego.geolocation.lat/lon/alt`
- `targets[]`: ID/class, relative position, relative velocity, longitudinal/lateral distance, closing speed, `ttc_simple`, `ttc_2d`, collision cone.
- `driver`: state, alertness score, eye state, head pose, mouth state và NTHU subject.
- `events_active[]`: event ID/type, age và actor IDs.
- `min_ttc`, `headway_sec`
- `behavior_flags`: harsh brake, harsh acceleration, harsh corner, speeding và tailgating.
- `risk`: base risk, driver factor và final risk score.

## 4. Kiểm Tra Chất Lượng Tín Hiệu

### Vehicle Motion

- Timestamp ổn định tuyệt đối ở 20 Hz, `dt = 0,05 s`.
- Speed suy ra từ sai phân `location.x/y` khớp `speed_kmh`, MAE chỉ từ **0,006 đến 0,014 m/s** tùy trip.
- `lateral_accel` tương quan tốt với `speed × yaw_rate`, hệ số tương quan từ **0,741 đến 0,969**.
- `location.x/y`, speed, yaw và lateral acceleration đủ tin cậy để dựng trajectory và kiểm tra động học.
- Acceleration có outlier: longitudinal acceleration xuống tới `-182,2 m/s²`, lateral acceleration lên tới `13,16 m/s²`. Bắt buộc dùng median/Hampel filter, giới hạn vật lý và event window; không cảnh báo từ một frame đơn.

### Driver State

Mỗi trip có 600 driver frame và 600 frame-level driver labels. Các trạng thái gốc gồm `alert`, `distracted`, `drowsy`, `yawning`, `microsleep`. Có thể dùng làm weak/ground-truth labels để benchmark DMS sau khi map về taxonomy thống nhất.

### Targets and Events

JSON có target class `vehicle`, `walker`, `bike`, target-relative motion và TTC ground truth. Đây là nguồn mạnh để:

- Đánh giá detector/tracker và custom labels.
- Đánh giá distance, closing speed và TTC.
- Tạo event windows từ scenario thay vì chấm từng frame độc lập.
- Kiểm tra compound risk với driver state.

## 5. Stereo Depth Benchmark Ban Đầu

Đã chạy StereoSGBM trên 5 frame depth có thật, cách đều, cho từng trip. Chỉ đánh giá pixel ở phần ảnh từ hàng 90 trở xuống và depth GT trong khoảng 0,5–90 m.

| Trip | Valid coverage | Median AE | Mean AE | Median AbsRel |
|---|---:|---:|---:|---:|
| T01 | 77,7% | 0,28 m | 2,34 m | 3,1% |
| T02 | 55,7% | 0,41 m | 1,42 m | 7,1% |
| T03 | 52,1% | 0,73 m | 3,59 m | 8,3% |
| T04 | 71,5% | 0,13 m | 2,15 m | 2,4% |
| T05 | 72,4% | 0,37 m | 2,90 m | 4,8% |
| T06 | 73,6% | 0,31 m | 2,09 m | 4,0% |

Trung bình theo trip: coverage khoảng **67,2%**, median absolute error khoảng **0,37 m**. T03 mưa lớn ban đêm là domain khó nhất. Kết quả này đủ tốt để đưa stereo depth vào C2 nếu:

- Có left-right consistency/confidence mask.
- Không điền depth giả cho sky, vùng texture thấp hoặc occlusion.
- Dùng temporal smoothing ở track/ROI thay vì làm mượt toàn ảnh.
- So sánh với GT 5 Hz và fallback về geometry/temporal estimate khi stereo invalid.

## 6. Thiết Kế Tính Năng Đề Xuất

### Fast-Corner Warning

Input:

- Speed.
- Filtered lateral acceleration.
- Filtered longitudinal acceleration.
- Yaw rate và speed limit để bổ trợ.

Baseline rule:

- Median filter 5 frame tại 20 Hz.
- Candidate khi speed tối thiểu 20 km/h và `|lateral_accel| >= 2,5 m/s²`.
- Giữ candidate ít nhất 0,25 giây.
- Critical khi `|lateral_accel| >= 4,0 m/s²`, hoặc đang phanh mạnh trong khi lateral acceleration cao.
- Dùng hysteresis và cooldown để tránh cảnh báo lặp.

Threshold này là baseline cần tune trên `behavior_flags.harsh_corner`, không phải ngưỡng an toàn pháp lý.

Output là `fast_corner` RiskEvent, có speed, peak lateral/longitudinal acceleration, yaw change, duration, severity và evidence window.

### Trip Trajectory Visualization

- Dùng trực tiếp `ego.location.x/y`, trừ vị trí bắt đầu và giữ aspect ratio 1:1.
- Màu điểm/đoạn đường biểu diễn speed.
- Kích thước hoặc độ sáng biểu diễn tổng acceleration; marker riêng cho harsh brake, fast corner, short TTC và DMS event.
- Vẽ heading arrow thưa theo yaw.
- Tooltip/panel hiển thị timestamp, speed, longitudinal acceleration và lateral acceleration.
- Xuất một PNG tổng kết và một visualization tương tác cho mỗi trip.

Không tích phân acceleration để tạo quỹ đạo vì world location đã chính xác hơn.

### Stereo Depth at 20 Hz

- Rectified `image_2/image_3` → disparity → `depth = fx × 0,30 / disparity`.
- Sinh depth, disparity và confidence/validity mask.
- Benchmark trên 120 GT depth frame/trip.
- Dùng ROI median/quantile có erosion khi gán depth cho object track.
- Lưu `depth_source = stereo`, quality score và fallback source trong output.

### IMU-Aware Horizon

- Lấy intrinsics từ `P2`.
- Lấy pitch/roll động từ JSON.
- Lấy rotation block từ `Tr_imu_to_velo`, `Tr_velo_to_cam`, `R0_rect`; hiện tại đều identity.
- Tính horizon line từ gravity vector bằng `l = K^{-T} g_camera`.
- Trừ camera mount bias bằng median attitude/road-plane reference của trip.
- Low-pass pitch/roll trước khi cập nhật horizon và lane/road ROI.

Horizon center shift p95 dưới khoảng 1,5 px ở hầu hết trip, nhưng T03 có frame đạt khoảng **18,8 px** do pitch 3,37°. Dynamic correction vì vậy là robustness feature, không phải thay thế road-plane fitting.

## 7. Mức Độ Tận Dụng

| Tín hiệu | Giá trị sử dụng | Độ tin cậy |
|---|---|---|
| Location, speed, yaw | Trajectory, heading, motion sanity check | Cao |
| Long/lat acceleration | Harsh behavior, fast corner, braking context | Cao sau filtering |
| P2/P3 và stereo images | Depth 20 Hz, object distance | Cao ở vùng có texture; cần confidence |
| GT depth 5 Hz | Stereo evaluation và calibration | Cao; `1000 m` nên coi là no-hit/far |
| Pitch/roll JSON | Dynamic horizon/ROI correction | Trung bình-cao sau smoothing |
| Identity IMU calibration | Static coordinate-chain input | Không phải dynamic IMU |
| Targets/TTC/behavior flags | Evaluation và event-window ground truth | Cao cho simulator |
| KITTI bbox gốc | Baseline/evaluation support | Cần audit vì đã thấy label thiếu/lệch |
| Driver state labels | DMS training/evaluation | Hữu ích nhưng phải kiểm tra domain leakage theo subject |
