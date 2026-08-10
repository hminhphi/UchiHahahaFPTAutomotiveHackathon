# FleetIQ Guardian Demo Captions

## Recording Asset

| Item | Value |
| --- | --- |
| Filename | `FleetIQ_Guardian_Round2_Demo.mp4` |
| Local packet path | `submission/UchiHahaha_FleetIQ_Guardian_Round2_Final/VIDEO/` |
| Format | H.264, 1440x900, silent |
| Measured duration | `04:08` |
| Status | Local draft recorded with Playwright; reviewer upload is still pending |

> [!IMPORTANT]
> This map is for captions or voice-over during the final edit. Keep the status
> statements and limitations intact. Do not describe the deterministic trip score
> as fleet ranking, fleet average, organizer accuracy, or blind-test accuracy.

## Caption Map

| Video time | On-screen action | Vietnamese narration / subtitle | Lower-third annotation |
| --- | --- | --- | --- |
| `00:00-00:25` | Fleet overview opens with the priority queue. | `FleetIQ Guardian giúp Fleet Safety Manager chọn chuyến cần xem và đi thẳng tới bằng chứng thay vì xem lại hàng giờ video.` | `Challenge #3 · Driver Intelligence Platform` |
| `00:25-00:55` | T01d appears in the fleet queue; the overview remains visible. | `Danh sách này là hàng đợi review. Điểm fleet chưa được xác thực để xếp hạng, nên chúng tôi chọn T01d để kiểm tra bằng chứng theo từng chuyến.` | `Trip review queue · not a fleet ranking` |
| `00:55-01:25` | T01d score ring and component breakdown appear. | `T01d có safety score 80 trên 100. Đây là điểm theo rule có thể audit: collision margin 98, driver attention 85, vehicle handling 97 và lane discipline 100.` | `Rule score · evidence score only` |
| `01:25-01:50` | The event list scrolls to the compound-risk event at frame 1010. | `Thay vì đọc cảnh báo rời rạc, reviewer chọn compound road and driver risk tại frame 1010 để mở mọi tín hiệu ở cùng bối cảnh.` | `Selected event · T01d / frame 1010` |
| `01:50-02:45` | Road replay, right stereo, driver monitor, depth map, and signal cards are visible. | `Road overlay giữ một xe trong hành lang với khoảng cách 20 phẩy 4 mét và TTC 1 phẩy 6 giây. Cùng frame, DMS báo drowsy với confidence 85 phần trăm.` | `Road + DMS + depth · synchronized` |
| `02:45-03:20` | Fused analysis and telemetry cards remain visible; replay time reads 00:50.5. | `Fusion worker đã sẵn sàng. Artifact cùng frame cho risk index 51, event code high TTC risk, driver drowsiness và compound risk. Telemetry hiển thị 46 km trên giờ và gia tốc dọc 3 phẩy 28 mét trên giây bình phương.` | `Risk index 51.0 · TTC 1.601 s` |
| `03:20-03:35` | Coaching and trajectory context remain in view. | `Coach không được suy diễn từ một ảnh đơn lẻ. Hành động coaching chỉ được gán sau khi road, driver state, TTC và telemetry đã được xem tại cùng khung hình.` | `Evidence-first coaching` |
| `03:35-04:08` | Recording returns to fleet overview. | `Workflow kết thúc tại fleet queue: chọn chuyến, kiểm tra event đồng bộ, và đưa ra coaching có căn cứ. Đây là review theo trip, không phải bảng xếp hạng toàn fleet.` | `Review workflow complete` |

## Required Final-Cut Addition

Append a `15-20` second segment after `04:08` before final upload:

1. Open `predictions/UchiHahaha/T01d.csv` at row `1010` and show `1010,50.500,1.601,drowsy,51.0`.
2. Run `uv run python tools/dataset/validate_submission.py --predictions-dir predictions/UchiHahaha` and show all ten files passing.
3. Use this narration: `CSV row 1010 khớp TTC, driver state và risk đã xem trên dashboard. Validator kiểm tra lại schema cho đủ mười trip trước khi nộp.`
4. Add lower-third: `Organizer-format CSV · 10/10 validation passed`.

## Final Edit Checklist

- Add Vietnamese voice-over or burn-in subtitles from the table above.
- Keep the original UI values visible; do not crop out the score caveats.
- Add the required CSV-validator segment and replace report timestamps with the final cut.
- Upload the final MP4 under the reserved filename and paste a reviewer-accessible URL into the report.
- Verify the URL in a private browser session before portal submission.
