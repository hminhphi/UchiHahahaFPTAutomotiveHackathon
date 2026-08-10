**KHUNG GỢI Ý DÀNH CHO ĐỘI THI**

**BÁO CÁO KẾT QUẢ CUỐI VÒNG 2 - FleetIQ Guardian**

Automotive Hackathon 2026

| BẢN CHẤT CỦA TÀI LIỆU NÀY Mục đích: Giúp đội trình bày tác phẩm và bằng chứng theo cách BGK có thể hiểu, kiểm tra và ghi nhận đầy đủ nhất. Không phải form compliance: Ngoài một số thông tin tiếp nhận bắt buộc, các mục còn lại là gợi ý. Đội có thể bỏ, gộp, đổi thứ tự, đổi định dạng hoặc thêm mục mới. Quyền chủ động: Đội tự quyết định thông tin nào cần thiết cho solution. Nội dung không được cung cấp sẽ không có căn cứ để reviewer tự suy đoán thay đội. Ưu tiên: Đầy đủ nhưng không lan man: claim rõ, observed result rõ và evidence dễ tìm quan trọng hơn số trang hoặc câu chữ marketing. |
| :---- |

| CÁCH SỬ DỤNG Khi chuẩn bị packet: Đội có thể chỉnh trực tiếp tài liệu này hoặc dùng cấu trúc riêng; ưu tiên phản ánh đúng trạng thái tại thời điểm nộp. Khi nộp final: Nộp một packet cuối qua kênh chính thức của BTC. Timestamp tiếp nhận là mốc dùng cho Vòng 2; cập nhật sau đó không tự động thay thế bản đã ghi nhận. Trước khi xóa một mục: Chỉ cần tự hỏi: bỏ mục này có khiến BGK thiếu căn cứ hiểu output, phần team-owned, chất lượng kỹ thuật, platform hoặc giá trị sử dụng hay không? |
| :---- |

**Thông tin tiếp nhận bắt buộc**

*Đây là phần hard schema để BTC định danh packet và kiểm tra khả năng truy cập; không phải phần tự chấm điểm.*

| Team ID / tên đội | UchiHahaha |
| :---- | :---- |
| **Đại diện / email Đội trưởng** | `[CẦN TEAM XÁC NHẬN TRƯỚC KHI UPLOAD]` |
| **Tên solution** | FleetIQ Guardian: Remote Driver Intelligence and Collision Risk Platform |
| **Mốc bản được báo cáo** | `v1.1.0`, 2026-08-10 |
| **Final report** | `Automotive_Hackathon_Final_Report_R2.md` |
| **Video demo dùng để chấm** | `[CẦN DÁN URL REVIEWER-ACCESSIBLE]` |
| **Evidence Folder** | `[CẦN DÁN URL REVIEWER-ACCESSIBLE]` |
| **Hướng giải pháp liên quan** | Digital Cockpit; Connected Car Services; Vehicle Middleware; AI-assisted safety analytics |

**Hướng giải pháp liên quan**

*\[x\] Digital Cockpit   \[x\] Connected Car Services   \[x\] Vehicle Middleware   \[x\] Agentic AI / AI-for-engineering   \[x\] Khác / giao thoa nhiều hướng*

| Nhóm nộp theo Challenge #3. Phần chấm điểm theo rule và phần TTC/near-miss là hai động cơ bên dưới, để chuyến đi không chỉ có cảnh báo mà còn có bằng chứng để xem lại. |
| :---- |
| **GÓI NỘP BÀI TỐI THIỂU** **Report:** Một tài liệu final ở định dạng BTC chấp nhận. **Video:** Bắt buộc; là căn cứ để BGK Vòng 2 quan sát demo khi không làm việc với live demo. **Evidence:** Link/file phải mở được bằng quyền truy cập dành cho reviewer; chỉ có URL không đồng nghĩa với truy cập hợp lệ. **Xác nhận:** Đội xác nhận packet phản ánh đúng trạng thái hiện tại và đã công bố phần mock/simulated/manual. |

**1\. Tổng quan solution   KHUYẾN NGHỊ**

| REVIEWER NÊN HIỂU ĐƯỢC TRONG KHOẢNG MỘT PHÚT • Solution cụ thể là gì và nằm trong workflow nào? • Ai trực tiếp sử dụng hoặc hưởng lợi? • Outcome chính mà đội muốn BGK quan sát là gì? • Điểm khác biệt đáng hiểu ngay từ đầu, nếu có. |
| :---- |

*Cách hiểu: đây không phải phần slogan. Một đoạn ngắn nhưng chỉ ra đúng sản phẩm, người dùng và outcome thường hữu ích hơn phần giới thiệu dài.*

**Nội dung của đội**

*Đội tự chọn cách trình bày: đoạn văn, sơ đồ, bảng, ảnh hoặc link evidence.*

| FleetIQ Guardian giúp người quản lý đội xe xem lại một chuyến đã hoàn thành. Họ mở điểm theo rule, chọn một sự kiện, rồi kiểm tra camera đường, DMS, depth và telemetry ở đúng cùng khung hình. Từ đó mới quyết định coaching. Điều nhóm muốn BGK thấy là một quy trình review có bằng chứng, không phải một màn hình xếp hạng đội xe. |
| :---- |

**2\. Core flow và phạm vi implementation   KHUYẾN NGHỊ**

| CÓ THỂ ĐỀ CẬP • Input → xử lý chính → output quan sát được. • Component nào tham gia và chúng gọi/tiêu thụ lẫn nhau như thế nào? • Đoạn nào chạy thật; đoạn nào partial, mock, simulated hoặc manual? • Môi trường chạy, dữ liệu và dependency quan trọng để hiểu kết quả. |
| :---- |

*Cách hiểu: core flow là chuỗi tạo ra outcome được chấm, không nhất thiết là toàn bộ architecture. Có thể dùng sơ đồ thay cho văn bản.*

**Nội dung của đội**

*Đội tự chọn cách trình bày: đoạn văn, sơ đồ, bảng, ảnh hoặc link evidence.*

| Nhãn road và GT depth tạo TTC cùng sự kiện trên đường. Camera tài xế đi qua MediaPipe geometry để tạo trạng thái DMS theo cửa sổ 15 frame. Sau đó telemetry, road và DMS được đưa vào RiskScorer để tạo event hợp nhất. Artifact được FastAPI phục vụ cho Next.js replay và coaching. Mỗi trip T01d-T10d có 1.800 logical frame. CarSky bridge mới ở mức Partial; nhóm chỉ claim Android Automotive end-to-end khi có video chạy thật. |
| :---- |

**3\. Baseline và phần team-owned   KHUYẾN NGHỊ**

*Cách hiểu: baseline là những gì đã tồn tại hoặc được cung cấp sẵn; team-owned là delta đội thực sự tạo ra trong solution. Mục tiêu là giúp reviewer không ghi điểm nhầm capability có sẵn thành giá trị mới của đội.*

| BASELINE / PHẦN ĐÃ CÓ | TEAM-OWNED / PHẦN ĐỘI LÀM |
| :---- | :---- |
| Starter kit cung cấp camera đường, camera tài xế, GT depth, calibration, telemetry, labels và TTC baseline. MediaPipe và YOLOP là capability bên ngoài. | Nhóm xây đường label YOLO v3, TTC từ depth ROI, DMS geometry state, smoothing 15 frame, gộp event, RiskScorer minh bạch, fusion API, replay có bằng chứng, coaching flow, CSV validator, dashboard và deck cuối. |

**Counterfactual / added value nếu cần**

*Nếu bỏ phần team-owned, outcome nào vẫn còn và outcome nào biến mất hoặc suy giảm? Có thể dùng before/after, ablation hoặc so sánh khác.*

| Nếu bỏ phần nhóm làm, reviewer vẫn có raw dataset và baseline. Nhưng sẽ không còn đường đi rõ ràng từ event đến khung hình bằng chứng, điểm theo rule, DMS timeline và coaching context. |
| :---- |

**4\. Output và evidence   TRUNG TÂM CỦA BÁO CÁO**

| CÁCH HIỂU OUTPUT RECORD Không giới hạn số lượng: Dùng số block vừa đủ cho các claim chính; đội có thể thay bằng bảng/format riêng nếu vẫn truy vết được. Expected khác observed: Expected/pass condition là căn cứ xác định đạt; observed result là điều hệ thống thực sự tạo ra ở bản final. Evidence locator: Không chỉ đưa link folder. Chỉ rõ file và timestamp/page/log/test ID để reviewer tìm đúng bằng chứng trong vài giây. Status: Real \= chạy thật; Partial \= một phần chạy thật; Mock/Simulated \= input hoặc môi trường mô phỏng; Manual \= còn thao tác thủ công; Planned \= chưa có output. |
| :---- |

**OUTPUT O1 — Điểm theo rule và review bằng chứng theo trip**

| Claim / outcome | Reviewer mở một trip, xem điểm theo rule đã chạy xong, phần điểm thành phần, timeline sự kiện và bằng chứng theo frame. |
| :---- | :---- |
| **Điều kiện xác định đạt** | Fusion summary có safety score và component scores. Trang trip hiển thị `Rule score` cùng `Fused analysis: Ready`. |
| **Kết quả quan sát** | Artifact cuối của T01d có risk `19.9`, safety `80.1`. Trên browser hiển thị `80/100`, với các phần `98/85/97/100`. |
| **Trạng thái** | Real |
| **Evidence locator** | `GET /api/v1/trips/T01d/analysis/fusion/summary`; `artifacts/trips/T01d/analysis/fusion/summary.json`; `http://localhost:3000/trips/T01d` |
| **Video timestamp** | `[CẦN ĐIỀN SAU KHI RECORD]` |
| **Caveat / giới hạn** | Đây là điểm theo rule cho từng trip. Nó không dùng để xếp hạng fleet, tính điểm trung bình fleet, hay nói thay cho blind-test accuracy và organizer score. |

**OUTPUT O2 — DMS timeline đã gộp event**

| Claim / outcome | DMS timeline chỉ giữ trạng thái đủ ổn định. Alert lặp được gộp lại để reviewer không phải đọc noise theo từng frame. |
| :---- | :---- |
| **Điều kiện xác định đạt** | Một state phải liên tục ít nhất 15 frame. Nếu cùng state quay lại trong 5 giây, hệ thống gộp nó vào event cũ. State khác vẫn xuất hiện như một event riêng. |
| **Kết quả quan sát** | Lần chạy cuối cho toàn bộ T01d-T10d tạo 61 DMS window. Không window nào ngắn hơn 15 frame. |
| **Trạng thái** | Real |
| **Evidence locator** | `artifacts/trips/<trip>/analysis/fusion/events.json`; `services/roadface-worker/tests/generate_ai_artifacts.py`; `docs/models/PROVENANCE_FINAL.md` |
| **Video timestamp** | `[CẦN ĐIỀN SAU KHI RECORD]` |
| **Caveat / giới hạn** | Runtime state đến từ MediaPipe geometry với smoothing 15 frame. Nhóm không dùng metric checkpoint offline để gọi đây là runtime accuracy. |

**OUTPUT O3 — Bằng chứng rủi ro đường tại frame 551 của T01d**

| Claim / outcome | Road artifact chỉ giữ object nằm trong ego corridor, sau đó liên kết object đó với GT-depth ROI và TTC evidence. |
| :---- | :---- |
| **Điều kiện xác định đạt** | `T01d` frame `551` có `Motorcycle` detection với non-null depth distance. |
| **Kết quả quan sát** | `Motorcycle`, confidence `0.3941`, bbox `(308.30,196.14)-(345.92,268.97)`, depth distance khoảng `5.02 m`. |
| **Trạng thái** | Real |
| **Evidence locator** | `artifacts/trips/T01d/analysis/road/000551.json`; `docs/proposal/UchiHahaha_FleetIQGuardian_Final_Round2.pdf` slide 6 |
| **Video timestamp** | `[CẦN ĐIỀN SAU KHI RECORD]` |
| **Caveat / giới hạn** | Frame này có thêm một pedestrian prediction chồng lên motorcycle do LocateAnything label conflict. Nhóm giữ lại false positive này để reviewer thấy giới hạn. TTC ở đây là GT-depth ROI proxy, không phải learned depth. |

**OUTPUT O4 — CSV đúng định dạng BTC**

| Claim / outcome | Xuất một CSV đúng schema cho mỗi trip T01d-T10d. |
| :---- | :---- |
| **Điều kiện xác định đạt** | Header đúng, 1.800 rows có thứ tự, TTC finite/`inf`, state hợp lệ, risk trong `[0,100]`. |
| **Kết quả quan sát** | Nhóm export lại 10 CSV từ artifact cuối và validator đều pass. Số finite TTC row lần lượt là T01d `176`, T02d `374`, T03d `85`, T04d `95`, T05d `478`, T06d `255`, T07d `67`, T08d `88`, T09d `234`, T10d `483`. |
| **Trạng thái** | Real |
| **Evidence locator** | `predictions/UchiHahaha/T01d.csv` through `T10d.csv`; `tools/dataset/validate_submission.py` |
| **Video timestamp** | `[CẦN ĐIỀN SAU KHI RECORD]` |
| **Caveat / giới hạn** | Ground truth cho redacted trips không có local; không suy diễn challenge accuracy trước organizer evaluation. |

*Đội có thể copy, rút gọn, gộp hoặc thay block này bằng cấu trúc riêng. Không có ngưỡng tối đa ba output.*

**5\. Chất lượng kỹ thuật và bằng chứng thực thi   NẾU PHÙ HỢP**

| CÓ THỂ ĐỀ CẬP • Architecture hiện tại và component/team boundary quan trọng. • Integration contract: API, signal, schema, protocol hoặc artifact exchange. • Test scenario, input/data, pass condition hoặc metric, oracle/ground truth và observed result. • Failure handling, edge case, fallback, log/trace và khả năng chẩn đoán. • Version/build/reproducibility hoặc artifact giúp đối chiếu implementation. |
| :---- |

*Cách hiểu: không cần điền mọi gợi ý để 'đủ form'. Chọn bằng chứng thể hiện độ tin cậy của solution. Nếu tài liệu thiết kế và code có drift, nêu implementation hiện tại và caveat thay vì giả định tài liệu luôn đúng.*

**Nội dung của đội**

*Đội tự chọn cách trình bày: đoạn văn, sơ đồ, bảng, ảnh hoặc link evidence.*

| Bản cuối chạy 10 trip, mỗi trip 1.800 frame. Có 18 focused Python test và 20 web test. Ruff, lint, typecheck, Docker production build, API và browser check đều pass. Riêng `T08d/1615`, source road-left không có. Hệ thống hiển thị marker unavailable, không thay bằng frame lân cận. Muốn chạy lại, xem `docs/runbooks/full-evidence-flow.md`; muốn bàn giao private runtime, xem `docs/runbooks/final-release.md`. |
| :---- |

**6\. Platform utilization / ecosystem alignment   15 ĐIỂM · CẦN EVIDENCE**

| CÓ THỂ ĐỀ CẬP • CarSky mapping: component/workload team-owned chạy tại node, ECU hoặc service nào và giao tiếp qua cơ chế nào? • Contract/capability nào của CarSky được tái sử dụng thay vì dựng lại? • Evidence nào chứng minh core flow end-to-end trên blueprint? • Phần nào chỉ là generic container/node, hosting, launcher/display, wrapper, mock hoặc planned? • AI-for-engineering: external system, workflow hoặc kỹ sư tiêu thụ capability qua interface/artifact nào? |
| :---- |

*Cách hiểu: Với solution không phải AI-for-engineering, đội cần có evidence cho thấy sự hiểu đúng và alignment thực chất với CarSky. Nếu không đủ căn cứ cho nội dung này, điểm Platform utilization (15 điểm) không được ghi nhận. Với AI-for-engineering, đội cần chứng minh capability được external consumer sử dụng thực tế qua interface hoặc artifact.*

**Nội dung của đội**

*Đội tự chọn cách trình bày: đoạn văn, sơ đồ, bảng, ảnh hoặc link evidence.*

| Nhóm có CarSky bridge container và coaching contract để nối vào integration path. Browser/API flow chạy thật bằng Docker Compose. Tuy vậy, Android Automotive HMI acknowledgement chưa có bằng chứng end-to-end trong packet này, nên trạng thái là Partial. Hệ thống cũng không gửi lệnh lái, phanh hay ga. |
| :---- |

**7\. Người dùng, buyer và khả năng triển khai   KHUYẾN NGHỊ**

| CÓ THỂ ĐỀ CẬP • Đội đang cung cấp/bán cái gì: app, service, module, SDK, tool hay internal solution? • Ai trực tiếp sử dụng và ai là buyer/process owner/người quyết định triển khai? • Mô hình tiếp nhận dự kiến: B2B, B2C, B2B2C, internal hay technology module? • Workflow hoặc outcome nào thay đổi cho người dùng/khách hàng? • Dependency bắt buộc: API, data, hardware, partner, approval; trạng thái real/mock/assumed/planned. • Bước kiểm chứng tiếp theo khả thi nhất và rào cản lớn nhất. |
| :---- |

*Cách hiểu: end user và buyer có thể là hai bên khác nhau. Nếu chưa có market evidence, đội có thể nêu giả thuyết nhưng nên phân biệt giả thuyết với integration/partnership đã tồn tại.*

**Nội dung của đội**

*Đội tự chọn cách trình bày: đoạn văn, sơ đồ, bảng, ảnh hoặc link evidence.*

| Người dùng trực tiếp là Fleet Safety Manager hoặc người review trip. Người mua hay chủ quy trình có thể là fleet operator, logistics safety owner hoặc OEM analytics team. Đây là một workflow B2B cho safety analytics và coaching. Khi triển khai thật, hệ thống cần camera/depth/telemetry ingestion, nơi lưu model và artifact, API/Web control plane, cùng CarSky integration nếu đội xe cần nó. |
| :---- |

**8\. Limitation, thay đổi và disclosure   KHUYẾN NGHỊ**

| CÓ THỂ ĐỀ CẬP • Known bugs, phần chưa hoàn tất hoặc điều kiện khiến output không ổn định. • Phần mock, simulated, manual hoặc video đã edit/cut. • Scope thay đổi so với proposal và ảnh hưởng đến claim/core flow. • Đóng góp solution-specific đáng kể từ mentor hoặc bên ngoài đội, nếu có. • Rủi ro, dependency hoặc giới hạn mà BGK cần biết để hiểu đúng kết quả. |
| :---- |

*Cách hiểu: disclosure không thay thế bằng chứng, nhưng giúp reviewer không đánh giá sai trạng thái hiện tại. Không cần viết biện hộ dài; ghi factual và map tới output liên quan.*

**Nội dung của đội**

*Đội tự chọn cách trình bày: đoạn văn, sơ đồ, bảng, ảnh hoặc link evidence.*

| Ground truth của redacted trip không có ở local. Vì vậy, điểm theo rule không phải accuracy hay ranking. Vùng x=`250..390` chỉ là image corridor cố định, không phải calibrated lane model. DMS runtime là geometry rule. T08d/1615 thiếu source road-left. Organizer data, weights, trip media và runtime ZIP không được public nếu chưa có approval. Trước khi upload portal, nhóm vẫn phải hoàn tất video, link evidence và thông tin liên hệ. |
| :---- |

**9\. Video demo dùng để chấm   BẮT BUỘC**

| VAI TRÒ CỦA VIDEO BGK Vòng 2: Đánh giá dựa trên report và video được BTC ghi nhận; không làm việc với live demo. Mentor: Xem live demo và xác nhận mức độ khớp giữa execution thực tế với report/video; note được chia sẻ cho đội và BTC. Đội thi: Chịu trách nhiệm để video thể hiện được claim, trạng thái và limitation đã khai. |  |  |  |
| :---- | :---- | :---- | :---- |
| **CÓ THỂ ĐỀ CẬP** **•** Input/data và precondition cần để hiểu demo. **•** Core flow và các output chính, ưu tiên mapping theo Output ID. **•** Timestamp map để reviewer tìm evidence nhanh. **•** Edge/failure case nếu nó quan trọng với claim. **•** Disclosure phần mock/simulated/manual hoặc edit/cut. |  |  |  |
| **Output ID** | **Timestamp** | **Điều cần quan sát** | **Ghi chú / disclosure** |
| O1 | `[CẦN ĐIỀN]` | Mở T01d, xem Rule score `80/100` và phần điểm thành phần | Artifact đã chạy trước; không phải fleet ranking |
| O2 | `[CẦN ĐIỀN]` | Chọn một DMS event đã gộp, rồi xem driver/road/telemetry cùng frame | MediaPipe geometry runtime, smoothing 15 frame, gộp state lặp trong 5 giây |
| O3/O4 | `[CẦN ĐIỀN]` | Xem motorcycle ở frame 551, sau đó mở 10 CSV và validator | Depth ROI proxy; redacted-trip evaluation vẫn do organizer thực hiện |

*Có thể thêm, bớt hoặc thay bảng trên bằng chapter/timestamp list của đội; không giới hạn ba dòng.*

**10\. Thông tin bổ sung đội muốn BGK xem xét   TÙY CHỌN**

*Dùng cho nội dung mà khung gợi ý chưa dự đoán: UX, data, security, benchmark, customer validation, innovation, experiment, appendix hoặc bất kỳ evidence nào đội cho rằng cần thiết.*

**Nội dung của đội**

*Đội có thể tạo heading mới thay vì giữ mục này.*

| Deck cuối là một cặp PPTX/PDF gồm 14 slide đã được review. `README.md` ở root có render kiến trúc rule và link đến submission, private release, model provenance và hướng dẫn chạy lại. Public source release không kèm organizer data, model weights, generated media hay private runtime handoff. |
| :---- |

**11\. Điểm mentor cần chú ý khi xác minh live demo   TÙY CHỌN**

*Chỉ ra Output ID, precondition hoặc điểm có khả năng bị hiểu khác giữa live execution và report/video. Đây không phải yêu cầu mentor hoàn thiện solution thay đội.*

**Nội dung của đội**

*Đội tự chọn cách trình bày: đoạn văn, sơ đồ, bảng, ảnh hoặc link evidence.*

| Hãy kiểm tra score T01d và `Fused analysis: Ready`. Chọn một DMS event để chắc rằng frame navigation đúng. Mở frame 551 để xem motorcycle evidence. Sau đó chạy `uv run python tools/dataset/validate_submission.py --predictions-dir predictions/UchiHahaha`. Nếu muốn claim CarSky, cần kiểm tra và record Android HMI riêng. |
| :---- |

**Xác nhận của đội**

*Đây là phần bắt buộc của packet final.*

**Đội xác nhận**

*\[ \] Report và video tương ứng với mốc bản đã khai.*<br>
*\[ \] Video/evidence link đã được kiểm tra bằng quyền truy cập dành cho reviewer.*<br>
*\[ \] Trạng thái Real / Partial / Mock / Simulated / Manual / Planned đã được công bố trung thực khi liên quan.*<br>
*\[ \] Đội hiểu việc thiếu thông tin/evidence có thể làm reviewer không có căn cứ ghi nhận claim.*<br>
*\[ \] Đội hiểu kết quả được chấm theo packet BTC ghi nhận tại thời điểm tiếp nhận; cập nhật sau đó không tự động thay thế bản đã ghi nhận.*<br>
*\[ \] Đội đồng ý mentor ghi nhận mức độ khớp/sai lệch giữa live demo với report/video và được quyền phản hồi note đó.*

| UchiHahaha |  |
| :---- | :---- |
| **Đại diện đội** | `[CẦN TEAM XÁC NHẬN]` |
| **Ngày hoàn thiện** | 10/08/2026 |
| **Tên file report final** | `Automotive_Hackathon_Final_Report_R2.md` hoặc BTC-accepted export |
