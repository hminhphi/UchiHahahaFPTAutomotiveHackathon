# Final Submission Checklist

## Already Prepared

- [x] Custom YOLO v3 labels exported for T01d-T10d.
- [x] Road, DMS, fusion, road-mask, depth, and replay artifacts refreshed.
- [x] All Docker demo services are healthy at `http://localhost:3000` and `http://localhost:8000`.
- [x] Road-left MP4 descriptor and byte-range streaming work.
- [x] Ten organizer-format CSVs exist under `predictions/UchiHahaha/`.
- [x] Submission validator passed all ten CSVs.
- [x] Organizer evaluator ran on full-GT `T01-Sample`; evidence is at `artifacts/evaluation/`.
- [x] Final report theo template BTC đã được cập nhật tại `docs/Automotive Hackthon - Final Vòng 2.docx.md`.
- [x] Final deck has reviewed PPTX and PDF exports.
- [x] Ready-to-complete archive is at `submission/UchiHahaha_FleetIQ_Guardian_Round2_Final_READY_FOR_UPLOAD.zip`.

## You Must Do

1. Điền tên/email đại diện, video URL, evidence URL và timestamp thật trong report theo template BTC.
2. Keep the official folder as `predictions/UchiHahaha/`. Keep the files named exactly `T01d.csv` through `T10d.csv`.
3. Re-run the validator immediately before upload:

   ```powershell
   uv run python tools/dataset/validate_submission.py --predictions-dir predictions/UchiHahaha
   ```

4. Record demo từ Docker build hiện tại. Đi từ T01d score đến event timeline, road evidence, DMS/depth/telemetry đồng bộ, rồi CSV validator. Chỉ đưa CarSky vào video nếu nó chạy live.
5. Replace the target timestamps in the report with actual video timestamps.
6. Create a reviewer-accessible evidence folder. Upload the final report, demo video, ten CSVs, screenshots or screen recording proof, validator output, model metrics, and source/build reference.
7. Test the video URL and evidence-folder URL from an incognito/private browser where you are not logged in.
8. If claiming CarSky platform points, run and record the Android Automotive HMI/bridge acknowledgement flow. Otherwise retain the `Partial` disclosure.
9. Export the report to the BTC-accepted format, preserve the final filename/version/timestamp, and submit the full packet through the official channel before the deadline.

## Do Not Claim

- Do not call redacted-trip TTC, driver state, or risk outputs ground truth.
- Do not claim YOLOP as the primary object detector.
- Do not hide the T01d frame-551 overlapping pedestrian prediction.
- Do not claim Android Automotive end-to-end behavior without recording it.
- Do not upload a CSV with invalid driver states such as `attentive` or `unknown`; the validator prevents this.
- Do not present a deterministic trip rule score as fleet ranking, fleet average, or blind-test accuracy.
