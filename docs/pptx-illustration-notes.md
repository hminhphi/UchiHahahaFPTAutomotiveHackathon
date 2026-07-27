# PPTX Illustration Notes

File này ghi lại các hình minh họa nâng cao nên bổ sung sau khi proposal deck đã ổn định về nội dung.

## Slide 5

- Hình đề xuất: ảnh thật hoặc render bán-thực của màn hình dashboard trong bối cảnh fleet operations.
- Mục tiêu: thay ảnh mockup hiện tại bằng một visual gần với sản phẩm web cuối cùng để tăng độ tin cậy khi pitching.
- Thành phần nên có: bảng xếp hạng tài xế, risk cards, trip timeline, evidence frame, coaching summary.

## Slide 7

- Hình đề xuất: khung near-miss evidence thật từ dữ liệu road-facing camera có overlay `TTC`, bounding box và confidence.
- Mục tiêu: chứng minh team không chỉ có dashboard mà còn có bằng chứng thị giác trực tiếp cho mỗi sự kiện rủi ro.
- Thành phần nên có: frame gốc, vùng lead vehicle, nhãn `short_ttc` hoặc `near_miss`, timestamp, tốc độ xe.

## Slide 9

- Hình đề xuất: sơ đồ kiến trúc vector hoặc isometric rõ 4 tầng `Inputs -> Engines -> Intelligence -> Outputs`.
- Mục tiêu: thay version text-heavy hiện tại bằng một sơ đồ pitch-ready có thể đọc trong 5 giây.
- Thành phần nên có: road cameras, driver camera, depth/calib, telemetry, TTC engine, scoring, fusion, dashboard/report.

## Slide 10

- Hình đề xuất: roadmap dạng Gantt ngắn với dependency rõ giữa `data contract`, `TTC/scoring`, `fusion/dashboard`, `demo package`.
- Mục tiêu: cho judge thấy kế hoạch 2-3 tuần có tính thực thi, không chỉ là các khối thời gian chung chung.
- Thành phần nên có: must-have, stretch goal, checkpoint review giữa tuần, backup demo assets.
