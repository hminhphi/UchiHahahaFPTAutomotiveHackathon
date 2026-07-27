# Plane lane audit results

## Test setup

Dataset: `Practice_Dataset`

Trips:

- `T01-Sample`
- `T02-Sample`
- `T03-Sample`
- `T04-Sample`
- `T05-Sample`
- `T06-Sample`

Sampling:

- 5 evenly spaced frames per trip.
- 30 frames total.
- Each frame is scored with plane inlier ratio, estimator confidence, corridor area, near/mid/far corridor width, metric offset and heading.

Outputs:

- `artifacts/roadface/plane_lane_audit_v1`
- `artifacts/roadface/plane_lane_audit_v2`

## V1 result

V1 used `z_near_m=4.0` for projecting the ego-lane corridor back into the camera view.

Problem:

- The road plane fit was strong, but the corridor started too far ahead of the ego vehicle.
- `near_width_ratio` was `0.0` on the audited frames because the corridor did not reach the near/bottom image region.
- Most frames were flagged with `bad_area;bad_near_width`.

Average scores:

| trip | avg | min | max |
|---|---:|---:|---:|
| T01-Sample | 81.8 | 81.5 | 82.9 |
| T02-Sample | 81.5 | 81.5 | 81.7 |
| T03-Sample | 81.4 | 80.4 | 82.3 |
| T04-Sample | 81.5 | 81.4 | 81.7 |
| T05-Sample | 81.4 | 80.6 | 81.9 |
| T06-Sample | 81.5 | 81.4 | 81.8 |

## Fix

Changed the near projection distance in `plane_lane_masks_from_centerline`:

```text
z_near_m: 4.0m -> 2.4m
```

Reason:

- The dataset camera height/intrinsics place the visible near road closer than 4m.
- The collision-risk corridor must cover the near ego-lane region, especially for objects immediately ahead.

## V2 result

After the fix, all 30 sampled frames pass the geometry score.

Average scores:

| trip | avg | min | max |
|---|---:|---:|---:|
| T01-Sample | 97.3 | 97.2 | 97.3 |
| T02-Sample | 97.2 | 97.2 | 97.2 |
| T03-Sample | 96.8 | 95.9 | 97.2 |
| T04-Sample | 97.2 | 96.9 | 97.3 |
| T05-Sample | 97.1 | 96.3 | 97.3 |
| T06-Sample | 97.2 | 97.2 | 97.3 |

Worst V2 frames:

- `T03-Sample` frame `000449`: score `95.9`, issues `ok`.
- `T05-Sample` frame `000300`: score `96.3`, issues `ok`.
- `T03-Sample` frame `000000`: score `96.5`, issues `ok`.
- `T04-Sample` frame `000000`: score `96.9`, issues `ok`.

## Regression command

```powershell
.venv\Scripts\python.exe scripts\roadface\audit_plane_lane.py --dataset practice --frames-per-trip 5 --output-dir artifacts\roadface\plane_lane_audit
```

## Interpretation

This audit validates the plane-based ego-lane corridor geometry, not an AI lane detector. The correct next step is still to replace the fallback road ROI with AI road/lane masks from YOLOP, HybridNets, SegFormer, CLRNet or external mask files.

## Curve-following update

The straight corridor was not sufficient for curved road samples. The estimator now adds a curve-aware path:

- Build lane-marking evidence from white/yellow markings and Sobel edges.
- Back-project those evidence pixels to the fitted road plane.
- Fit a polynomial centerline in metric `X-Z` space.
- Use polynomial degree 2 when the evidence spans enough depth bins.
- Anchor the polynomial center at the lookahead distance to the road-plane centerline, so the curve shape can be used without drifting into the adjacent lane.

New artifacts:

- `artifacts/roadface/curve_lane_fix/T01_000324_curve_v3.png`
- `artifacts/roadface/plane_lane_audit_curve_v3`
- `artifacts/roadface/test_lane_masks_redacted_curve_v3`

Important limitation:

- If a curved scene has weak lane markings, heavy occlusion, or bad depth support, the estimator intentionally falls back to the safer road-plane centerline.
- This is still not a replacement for a real AI lane segmentation model; AI masks should be plugged in through `--mask-source files` or `--mask-source transformers`.

## Single-boundary correction

The first curve-aware version could bend in the wrong direction because it tried to infer the lane center directly from mixed lane evidence. The safer correction is:

- Fit left and right lane boundaries separately in road-plane `X-Z` space.
- If only the left boundary is reliable, infer the right boundary by shifting by the lane width.
- If only the right boundary is reliable, infer the left boundary by shifting by the lane width.
- Anchor the inferred lane center to the road-plane centerline so it does not drift into an adjacent lane.
- Reject the curved boundary fit if it produces unsafe offset or heading, then fall back to road-plane centerline.
- Start the projected corridor from the bottom camera ray intersecting the road plane instead of from a fixed near distance.

Latest artifacts:

- `artifacts/roadface/curve_lane_fix/T01_000324_single_boundary_bottomray.png`
- `artifacts/roadface/plane_lane_audit_single_boundary_bottomray`
- `artifacts/roadface/test_lane_masks_redacted_single_boundary_bottomray`
