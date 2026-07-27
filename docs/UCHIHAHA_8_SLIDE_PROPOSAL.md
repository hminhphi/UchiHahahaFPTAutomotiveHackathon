# UchiHaha - Proposal Deck 8 Slides

## Mục tiêu truyền thông

Sau phần trình bày, giám khảo nên thấy rõ vì sao UchiHaha xứng đáng vào Vòng 2: **FleetIQ Guardian** là một hướng full vertical khả thi, có nền tảng nghiên cứu rõ ràng, phát hiện được risk event, đưa ra evidence, chấm trip score và hỗ trợ coaching an toàn qua IVI.

## Nhịp kể chuyện và Table of Content

Giữ thanh Table of Content ở chân trang, chỉ tô cam phần đang trình bày.

1. **Thông tin đội chơi** — Slide 1
2. **Bài tập lựa chọn** — Slide 2
3. **Vấn đề & cách giải quyết** — Slide 3–7
4. **Lộ trình Vòng 2** — Slide 8

Thời lượng đề xuất: 8–10 phút. Dành phần lớn thời gian cho Slide 4–7.

---

## Slide 1 — UchiHaha xây dựng safety intelligence, không chỉ một dashboard giám sát

**Section:** Thông tin đội chơi

**Title**

UchiHaha × FleetIQ Guardian

**Sub title**

Driver Intelligence full vertical: từ multi-source signals đến safety action

**Nội dung hiển thị**

- Road Intelligence: object, distance, relative motion, TTC, lane context.
- Driver Intelligence: buồn ngủ, mất tập trung, hành vi nguy hiểm, confidence.
- Platform Intelligence: fusion, explainable score, dashboard, IVI coaching.
- Một đội, một pipeline, một end-to-end demo.

**Hình ảnh minh họa**

- Hình chính: ảnh AI `Slide 1 - Cover Hero` trong `docs/AI_IMAGE_PROMPTS.md`.
- Dải phụ tuỳ chọn: `artifacts/pptx-assets/team-composition.png`.
- Không dùng architecture diagram dày đặc trên slide mở đầu.

**Caption**

`Detect → Explain → Score → Coach`

**Layout đề xuất**

- Hero visual full-bleed ở 58% bên phải.
- 42% bên trái chứa title, subtitle và ba nhóm năng lực.
- Tên đội màu cam; tên sản phẩm màu trắng.
- Thanh TOC ở chân trang, highlight `Thông tin đội chơi`.

**Script cho speaker**

"Chúng tôi là UchiHaha. Chúng tôi xây dựng FleetIQ Guardian, một nền tảng biến road video, driver camera và telemetry thành safety intelligence có thể hành động. Điểm khác biệt không nằm ở một model riêng lẻ, mà ở cách kết nối ba năng lực: hiểu môi trường quanh xe, hiểu trạng thái tài xế và hiểu risk ở cấp chuyến đi. Kết quả phục vụ hai nhóm người dùng cùng lúc: Fleet Manager cần evidence để ưu tiên can thiệp; tài xế cần cảnh báo ngắn gọn, đúng lúc và an toàn. Trong tám slide, chúng tôi sẽ cho thấy đây là một kiến trúc full vertical đủ thực tế cho MVP hackathon, đồng thời đủ sâu để phát triển thành sản phẩm automotive."

---

## Slide 2 — Chúng tôi chọn đề bài bao trọn full vertical

**Section:** Bài tập lựa chọn

**Title**

Driver Intelligence Platform là lựa chọn full vertical

**Sub title**

Ba tầng sản phẩm, một unified dashboard, một closed-loop có kiểm soát

**Nội dung hiển thị**

- Live Fleet Monitor: vị trí, trạng thái và risk real-time.
- Behavior Analytics: xu hướng theo tài xế, chuyến, tuyến và thời gian.
- Risk Intelligence: fusion score có giải thích và event evidence.
- Bonus: IVI coaching qua safety gate.

**Hình ảnh minh họa**

- Hình chính: `artifacts/diagrams/08_full_vertical_product_map.png`.
- Nếu hình dày, crop tập trung vào ba tầng sản phẩm.
- Thêm một mũi tên cam mảnh cho Fleet-to-Vehicle feedback.

**Caption**

`Một dataset chung cho monitor, analytics, risk scoring và coaching.`

**Layout đề xuất**

- Title và subtitle chiếm 20% phía trên.
- Product-map diagram chiếm 62% trung tâm.
- Bốn output nằm trên một dòng cuối, không dùng bốn card.
- Highlight `Bài tập lựa chọn` trong TOC.

**Script cho speaker**

"Chúng tôi chọn Driver Intelligence Platform vì đây là đề bài tận dụng đầy đủ nhất dataset chung. Live Fleet Monitor trả lời câu hỏi: xe nào đang cần chú ý ngay lúc này. Behavior Analytics cho biết hành vi nào lặp lại theo tài xế, tuyến đường hoặc thời gian. Risk Intelligence giải thích mức độ nguy hiểm, nguyên nhân và bằng chứng. Ba tầng này không phải ba sản phẩm tách rời; chúng dùng chung một data flow và một event schema. Chúng tôi cũng đóng vòng lặp bằng IVI coaching, nhưng chỉ sau safety gate. Cách tiếp cận này đáp ứng toàn bộ output bắt buộc và thể hiện tư duy hệ thống của một sản phẩm automotive thực tế."

---

## Slide 3 — Vấn đề không phải thiếu dữ liệu, mà thiếu ngữ cảnh chung

**Section:** Vấn đề & cách giải quyết

**Title**

Một tín hiệu riêng lẻ không đủ để giải thích khoảnh khắc nguy hiểm

**Sub title**

Risk chỉ đáng tin khi kết hợp road context, vehicle dynamics và driver state.

**Nội dung hiển thị**

- Raw video mất thời gian review và khó truy nguyên nguyên nhân.
- Lệch timestamp có thể khiến hệ thống hiểu sai risk.
- Ngưỡng cảnh báo cứng dễ báo nhầm, khiến người dùng bỏ qua cảnh báo.
- Fleet Manager cần evidence, severity, explanation và recommended action.

**Hình ảnh minh họa**

- Hình chính: ảnh AI `Slide 3 - Raw Signals To Action`.
- Thay thế: `artifacts/diagrams/06_risk_case_examples.png`.
- Chỉ minh họa một case: distraction + low TTC + high speed.

**Caption**

`Low TTC chỉ là tín hiệu; synchronized compound event mới là intelligence.`

**Layout đề xuất**

- Chia 55/45.
- Bên trái: một compound-risk visual với timestamp đồng bộ.
- Bên phải: bốn bullet và một câu takeaway màu cam.
- Không dùng lưới problem-card chung chung.

**Script cho speaker**

"Dữ liệu không thiếu; vấn đề là ý nghĩa đang nằm rời rạc ở nhiều stream. TTC thấp không phải lúc nào cũng nguy hiểm: xe có thể đang chạy song song, object có thể ở làn khác, hoặc tài xế đang phanh để phục hồi. Ngược lại, một khoảnh khắc mất tập trung rất ngắn có thể trở nên nghiêm trọng khi tốc độ cao và khoảng cách đang giảm nhanh. Nếu các stream lệch timestamp, hệ thống có thể gán sai nguyên nhân. Nếu chỉ dùng một ngưỡng cảnh báo cố định, dashboard sẽ báo nhầm nhiều; lâu dần Fleet Manager và tài xế sẽ bỏ qua cả cảnh báo thật. Vì vậy, chúng tôi tập trung vào đồng bộ thời gian, tạo context đa phương thức, rồi chuyển nó thành event có severity, confidence, evidence và recommended action."

---

## Slide 4 — Pipeline đồng bộ ba luồng thành một risk event

**Section:** Vấn đề & cách giải quyết

**Title**

Pipeline tách perception, fusion và decision

**Sub title**

Đủ modular để debug, đủ unified để suy luận multi-modal

**Nội dung hiển thị**

- Road model: object, distance, relative motion, TTC, lane offset.
- DMS: drowsiness, distraction, gaze, phone và seatbelt risk.
- Telemetry: braking, acceleration, steering và turn-signal context.
- Temporal fusion: event, severity, confidence và explanation.
- Output: dashboard, trip score, report và IVI safety gate.

**Hình ảnh minh họa**

- Hình chính: `artifacts/diagrams/00_fleetiq_processing_pipeline.png`.
- Đây là bản online pipeline, chủ ý không có training loop.
- Ưu tiên SVG để hình sắc nét khi trình chiếu.

**Caption**

`Ba input clocks → aligned windows → một auditable event schema.`

**Layout đề xuất**

- Diagram chiếm 75% diện tích slide.
- Năm bullet thành nhãn đánh số dưới từng stage.
- Chỉ dùng cam cho Risk Intelligence và back-to-car path.
- Không đặt paragraph cạnh diagram.

**Script cho speaker**

"Kiến trúc online được tách thành ba lớp. Lớp perception chỉ trả về observation có confidence, chưa tự kết luận risk. Road branch tạo object track, distance, relative speed, TTC và lane context. Driver branch tạo driver state theo thời gian, vì một frame nhắm mắt chưa đủ để kết luận buồn ngủ. Telemetry branch không cần model nặng: nó chuẩn hóa đơn vị, resample timestamp và tạo feature như harsh braking hoặc steering jerk. Alignment layer gom dữ liệu vào các window một, ba và năm giây. Risk model nhận feature đã căn chỉnh rồi xuất event thống nhất cho dashboard, trip score và safety gate. Cách tách lớp này giúp benchmark từng nhánh và truy vết lỗi khi demo."

---

## Slide 5 — Geometry giữ phần vật lý; temporal AI học tổ hợp risk

**Section:** Vấn đề & cách giải quyết

**Title**

Automotive physics và lightweight AI cùng tạo quyết định đáng tin

**Sub title**

Deterministic features anchor model; machine learning học compound risk
 
 
**Nội dung hiển thị**

- Distance kết hợp depth ROI, calibration và road-plane geometry.
- Relative speed lấy từ biến thiên distance đã smoothing.
- TTC chỉ hợp lệ khi object đang tiến gần đáng kể.
- Driver state cần temporal persistence và calibrated confidence.
- Online fusion dùng GBDT; temporal network là stretch goal.
- LLM chỉ gắn semantic label sau clustering; không tham gia train.

**Hình ảnh minh họa**

- Trái: `paper/extracted_figures/caption_crops/Ali_Real-time_vehicle_distance_estimation_using_single_/Ali_Real-time_vehicle_distance_estimation_using_single__p001_figcap01.png`.
- Giữa: `paper/extracted_figures/caption_crops/2303.09551v2/2303.09551v2_p003_figcap01.png`.
- Phải: equation và aligned feature-window tự dựng.
- Có thể thay bằng ảnh AI `Slide 6 - Road-view Intelligence`.

**Equation trên slide**

`TTC = distance / closing_speed`, chỉ khi `closing_speed > epsilon`.

**Source footer**

`Ali et al., WACV 2020 | Wei et al., SurroundOcc, ICCV 2023 | Hassan et al., DMS Survey, 2026`

**Caption**

- `Geometry anchors metric distance.`
- `Multi-camera features bổ sung surrounding context.`
- `Temporal fusion học compound risk.`

**Layout đề xuất**

- Editorial layout ba cột: 34% / 28% / 38%.
- Crop paper figure đến đúng vùng Figure, bỏ phần text bài báo.
- Đặt equation trong khối navy, nhấn denominator màu cam.
- Citation footer cỡ 10–12 pt.

**Script cho speaker**

"Slide này là cầu nối giữa hai nhóm giám khảo. Với automotive, distance không nên là một kết quả từ model mà không kiểm chứng được. Chúng tôi ưu tiên depth ROI khi có depth ground truth, dùng calibration và road-plane geometry làm baseline hoặc sanity check. Với mỗi object track, relative velocity được tính từ distance đã smoothing; hai xe chạy song song sẽ có closing speed gần như bằng không. TTC chỉ hợp lệ khi closing speed dương và đủ lớn, nhờ đó tránh cảnh báo từ nhiễu nhỏ. Với AI, các physical features và DMS confidence được gom theo time window. MVP dùng GBDT vì nhẹ, dễ giải thích và hợp với dữ liệu tabular; TCN hoặc GRU là stretch goal. Sau inference, risk embeddings được clustering; LLM 4–8B chỉ gắn semantic label cho từng cluster để hỗ trợ analytics. Nhãn LLM không đi vào training dataset, và LLM không nằm trên safety-critical path."

---

## Slide 6 — Mỗi risk event trở thành evidence, score và safety action

**Section:** Vấn đề & cách giải quyết

**Title**

Một event dùng chung cho fleet decision và driver coaching

**Sub title**

Event schema chung giúp mọi product surface kể cùng một câu chuyện

**Nội dung hiển thị**

- Dashboard xếp hạng xe theo current risk và accumulated risk.
- Timeline đồng bộ video, TTC, DMS và telemetry evidence.
- Trip score giải thích penalty theo severity, duration và context.
- Coaching đề xuất ba cải thiện cụ thể sau mỗi chuyến.
- IVI chỉ nhận advisory khẩn cấp, confidence cao, không lặp.

**Hình ảnh minh họa**

- Hình chính: ảnh AI `Slide 12 - Fleet Manager Dashboard`.
- Inset: ảnh AI `Slide 13 - Back-to-Car / IVI Coaching`.
- Architecture cue: `artifacts/diagrams/09_closed_loop_back_to_car.png`.
- Fallback hiện có: `artifacts/pptx-assets/dashboard-preview.png`.

**Caption**

`Detect once; explain consistently across dashboard, report và vehicle.`

**Layout đề xuất**

- Dashboard mockup chiếm 68% bên trái.
- IVI inset ở góc phải dưới, nối bằng một mũi tên cam.
- Năm output nằm trong right rail hẹp, chỉ dùng text.
- Không đặt full diagram và full mockup cùng lúc.

**Script cho speaker**

"Mỗi event có chung schema: vehicle, driver, timestamp, location, risk label, severity, confidence, evidence URI và recommended action. Nhờ đó, dashboard, report và IVI không kể ba câu chuyện khác nhau. Fleet Manager có thể đi từ fleet map vào một xe, mở timeline đồng bộ, xem evidence frame và hiểu vì sao trip score bị trừ. Score bắt đầu từ 100, trừ penalty theo severity, duration, confidence và context multiplier; phản ứng an toàn như phanh kịp thời có thể nhận recovery bonus. Back-to-car là bonus có kiểm soát: chỉ event khẩn cấp, confidence cao, latency hợp lệ và chưa bị lặp mới được gửi vào IVI. Các event còn lại chuyển sang post-trip coaching để tránh alert fatigue."

---

## Slide 7 — Niềm tin đến từ kiểm soát false alarm, không chỉ accuracy

**Section:** Vấn đề & cách giải quyết

**Title**

Safety, explainability và reproducibility là acceptance gates

**Sub title**

Mỗi model phải chứng minh giá trị vận hành trước khi tham gia closed-loop

**Nội dung hiển thị**

- Road: distance error, TTC stability, critical-event recall.
- DMS: PR-AUC, calibration, detection delay, false alarms/hour.
- Fusion: event F1, severity agreement, cross-trip robustness.
- Platform: latency, replay determinism, evidence completeness.
- IVI: confidence gate, cooldown, fallback, intervention log.

**Hình ảnh minh họa**

- Hình chính: ảnh AI `Slide 17 - Evaluation And Safety`.
- Dải phụ: `artifacts/diagrams/11_proposal_demo_storyboard.png`.
- Có thể thêm một evidence thumbnail từ starter dataset.

**Caption**

`Không metric nào đủ một mình; mọi alert đều phải review được.`

**Layout đề xuất**

- 60% trái: năm acceptance gate theo dạng bậc thang.
- 40% phải: evidence chain từ frame đến event và report.
- Dùng xanh lá tiết chế cho gate đạt; cam cho gate chờ.
- Dùng source footer, không đặt bibliography block.

**Source footer**

`DMS evaluation principles: Hassan et al., 2026 survey.`

**Script cho speaker**

"Giám khảo automotive sẽ quan tâm false alert và fail-safe; giám khảo AI sẽ quan tâm split, calibration và generalization. Chúng tôi dùng một bộ acceptance gate chung để trả lời cả hai nhóm câu hỏi. Road model không chỉ báo mAP; nó phải có distance error và TTC stability. DMS không chỉ báo accuracy; nó cần PR-AUC, calibration, time-to-detect và false alarms per hour. Fusion model được đánh giá trên event, không phải từng frame, và train-test split phải tách theo trip để tránh leakage. Toàn bộ pipeline phải replay cùng một trip ra cùng event và cùng score. IVI có confidence threshold, cooldown, network fallback và intervention log. Nếu safety gate chưa đạt, hệ thống vẫn tạo giá trị out-car, nhưng không gửi cảnh báo vào xe."

---

## Slide 8 — Vòng 2 kết thúc bằng một closed-loop story có thể replay

**Section:** Lộ trình Vòng 2

**Title**

Ưu tiên chứng minh core flow trước khi polish giao diện

**Sub title**

Ba tuần build theo risk kỹ thuật, kết thúc bằng một demo end-to-end rõ ràng

**Nội dung hiển thị**

- Week 1: loader, synchronization, calibration và physics baseline.
- Week 2: fusion model, score engine, scenario replay, cluster labeling.
- Week 3: dashboard, evidence pack, coaching report, IVI shadow mode.
- Acceptance gates: reproducible event, metric, confidence và fallback.
- Final demo: replay một trip từ detection đến coaching.

**Hình ảnh minh họa**

- Hình chính: ảnh AI `Slide 15 - Implementation Roadmap`.
- Dải storyboard: `artifacts/diagrams/11_proposal_demo_storyboard.png`.
- Accent tuỳ chọn: ảnh AI `Slide 18 - Closing Product Loop`.
- Badge đổi mới nên có: `Scenario Replay`, `Evidence Pack`, `Risk Cluster Library`, `Shadow-mode IVI`.

**Caption**

`Input trip → synchronized event → explainable score → coaching / IVI shadow mode.`

**Layout đề xuất**

- Roadmap 3 tuần chiếm 60% phía trên, mỗi tuần một lane.
- Bottom storyboard thể hiện input trip đến coaching / IVI shadow mode.
- Badge đổi mới đặt thành dải nhỏ phía trên storyboard.
- Kết thúc bằng dòng cam: `Select UchiHaha for Round 2.`
- Highlight `Lộ trình Vòng 2` trong TOC.

**Script cho speaker**

"Vòng 2 được chia theo risk kỹ thuật, không chia theo từng màn hình. Tuần đầu chốt data foundation: loader, timestamp, depth, calibration, object tracking, TTC baseline, DMS baseline và telemetry normalization. Tuần hai xây risk intelligence: aligned feature window, fusion model, confidence calibration, trip score, scenario replay và risk cluster library. LLM chỉ đặt tên semantic cho cluster sau clustering, để reviewer hiểu pattern risk; nó không tạo training label. Tuần ba biến core flow thành sản phẩm: fleet dashboard, evidence pack, coaching report, alert log và IVI shadow mode qua safety gate. Demo cuối cùng là một câu chuyện liền mạch: mở fleet map, chọn risky trip, xem TTC và DMS trên timeline, mở evidence, giải thích score, rồi xem coaching hoặc intervention log. Definition of done không phải một video đẹp; đó là một trip có thể replay, có metric, có bằng chứng và có fallback."

---

## Visual direction chung

- Tỷ lệ 16:9; tối giản, enterprise automotive, tương phản cao.
- Màu: navy `#19226D`, cam `#F37021`, xanh `#034EA2`, warm white.
- Typography: geometric sans đậm cho title; sans dễ đọc cho body.
- Cỡ chữ: title ≥ 35 pt, subtitle 24 pt, body 18–22 pt.
- Mỗi slide chỉ có một dominant visual; tránh lạm dụng card grid.
- Chỉ dùng cam cho quyết định, rủi ro và back-to-car path.
- Giữ thanh TOC footer, highlight section hiện tại.
- Chỉ dùng progressive reveal nhẹ ở Slide 4, 5 và 8.

## Lưu ý sử dụng asset

- Ưu tiên SVG trong `artifacts/diagrams` khi chèn vào PowerPoint.
- Crop paper figure sát nội dung và giữ citation footer.
- Không trình bày paper figure như kết quả thử nghiệm của UchiHaha.
- Thay fake text trong mockup bằng label ngắn hoặc blur.
- Không claim latency, accuracy hoặc performance khi chưa đo.
- Thay role trên Slide 1 bằng tên thành viên khi đã xác nhận.

## Các câu hỏi giám khảo đã được deck trả lời

- **Automotive:** Distance tính thế nào? TTC khi nào hợp lệ? Cách tránh alert fatigue?
- **AI:** Đồng bộ stream ra sao? Vì sao GBDT? LLM label cluster ở đâu?
- **Product:** Ai dùng output? Dashboard hiển thị gì? Back-to-car tạo giá trị nào?
- **Hackathon:** MVP là gì? Demo thế nào? Tiêu chí hoàn thành là gì?
