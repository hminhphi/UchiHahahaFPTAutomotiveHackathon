# Lane Detection Kaggle/Hough Improvement Audit

## What Changed

The lane/corridor estimator now uses a Kaggle-style classical lane detector as an evidence booster, not as the final geometry source:

- Canny + Gaussian blur + road ROI + probabilistic Hough lines generate observed lane-marking evidence.
- Hough segments are accepted only when they overlap likely lane colors: white or yellow markings.
- Lane boundaries are projected onto the road plane before fitting, so interpolation happens in metric ground coordinates.
- Paired left/right boundary fits are preferred over single-boundary extrapolation.
- Single-boundary extrapolation is rejected when the visible boundary diverges from the ego-road center in a way that suggests an adjacent lane divider.
- KITTI object labels are converted into an ignore mask so cars, cyclists, and pedestrians do not become lane-marking evidence.

This is intentionally conservative for collision-risk filtering: a safe fallback corridor is preferred over a confident but wrong curved lane.

## Key Commands

```powershell
.venv\Scripts\python.exe scripts\roadface\audit_plane_lane.py --dataset practice --frames-per-trip 5 --output-dir artifacts\roadface\plane_lane_audit_kaggle_hough_object_ignore --render
.venv\Scripts\python.exe scripts\roadface\audit_plane_lane.py --dataset redacted --frames-per-trip 5 --output-dir artifacts\roadface\plane_lane_audit_redacted_kaggle_hough_object_ignore --render
```

## Practice Audit

- Frames audited: 30
- Trips audited: T01-Sample to T06-Sample
- Worst score: 89.3 on T05-Sample frame 000300
- All frames reported `issues=ok`
- Critical T01-Sample frame 000300 now uses `paired-boundary` and follows the left curve instead of extrapolating the wrong direction.

Artifacts:

- `artifacts/roadface/plane_lane_audit_kaggle_hough_object_ignore/plane_lane_audit.csv`
- `artifacts/roadface/plane_lane_audit_kaggle_hough_object_ignore/plane_lane_audit_summary.md`
- `artifacts/roadface/plane_lane_audit_kaggle_hough_object_ignore/plane_lane_contact_sheet.png`
- `artifacts/roadface/kaggle_hough_object_ignore/T01_000300_final.png`

## Redacted/Test Audit

- Frames audited: 50
- Trips audited: T01d to T10d
- Most trips average above 90
- Worst frame: T09d frame 001799, score 47.6
- The worst frame is a close-front-car occlusion case, not a curve-direction failure. The vertical corridor still covers the obstacle for collision-risk filtering.

Artifacts:

- `artifacts/roadface/plane_lane_audit_redacted_kaggle_hough_object_ignore/plane_lane_audit.csv`
- `artifacts/roadface/plane_lane_audit_redacted_kaggle_hough_object_ignore/plane_lane_audit_summary.md`
- `artifacts/roadface/plane_lane_audit_redacted_kaggle_hough_object_ignore/plane_lane_contact_sheet.png`
- `artifacts/roadface/kaggle_hough_object_ignore/T09d_001799_final.png`

## Remaining Edge Cases

- Close front vehicles can occlude the visible lane. The current behavior keeps a vertical risk corridor over the vehicle, which is good for TTC/collision filtering, but the visual lane-line overlay may appear on top of the object.
- Weak or missing depth can force `flat_ground_fallback`; this remains usable for demo filtering but should be marked lower confidence.
- For a stronger AI path, replace classical road ROI with an external road/lane segmentation model such as YOLOP, HybridNets, SegFormer/Cityscapes, CLRNet, or PersFormer, then feed the masks into the same plane-based metric corridor stage.
