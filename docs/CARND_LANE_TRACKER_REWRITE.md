# CarND Lane Tracker Rewrite

## Reference

Primary reference:

- https://github.com/yang1688899/CarND-Advanced-Lane-Lines

Relevant files in the reference repository:

- `pipeline.py`: complete frame/video pipeline and temporal line state.
- `utils.py`: perspective transform, histogram seeds, sliding windows, search around a previous polynomial, curvature, offset, and inverse-warp rendering.
- `line.py`: accepted-fit history and temporal averaging.
- `writeup.md`: rationale and visual examples.

## What the reference repository does

The reference pipeline is a classical lane geometry pipeline:

1. Undistort the camera image.
2. Build a binary lane-pixel image from gradient and color thresholds.
3. Warp the binary image to a bird's-eye view.
4. Find left/right histogram peaks.
5. Collect pixels with sliding windows.
6. Fit `x(y)` as a second-order polynomial.
7. On subsequent frames, search around the previous polynomial.
8. Compute lane curvature and lateral offset in bird's-eye coordinates.
9. Inverse-warp the lane corridor onto the road image.

The important idea is not the Sobel/HLS thresholding. For FleetIQ, YOLOP already
provides the AI lane-line mask. The useful part is the geometry after that mask:
IPM, lane-pixel association, polynomial fitting, pair validation, and temporal
tracking.

## Problems in the former FleetIQ implementation

The former default fitted connected components directly in the perspective
camera image. This caused several failure modes:

- Near-camera pixels dominated the fit.
- A missing bottom fragment broke bottom-up tracing.
- Two independently fitted boundaries could curve in opposite directions.
- A dense curb or adjacent marking could win only because it contained more
  pixels.
- A constant pixel shift in camera space did not preserve physical lane width
  on a ground plane.

## New implementation

Core implementation:

- `scripts/roadface/carnd_lane_tracker.py`

Visualizer and tuner:

- `scripts/roadface/visualize_yolop_lane_offset.py`

The default association method is now `birdseye`.

### Main differences from the 2017 reference

- Uses YOLOP's learned lane mask instead of color/gradient thresholding.
- Uses normalized perspective points for 640x360 and other resolutions.
- Builds a histogram from multiple vertical bands, so a valid bottom row is not
  required.
- Starts sliding windows at the strongest supported vertical band and sweeps
  both upward and downward.
- Uses iterative residual rejection before accepting a quadratic fit.
- Checks bird's-eye lane width, width variance, parallel slope, and whether the
  corridor brackets the ego camera.
- If one boundary is missing or unreliable, shifts the reliable bird's-eye
  polynomial by one lane width. This preserves the same curvature.
- Rejects dense curb candidates when their inferred corridor moves away from
  the ego center.
- Searches around the previous fit and smooths accepted polynomials for video.

## Parameters to tune

The most important tuner controls are:

- `persp_top_y_pct`: vertical start of the ground-plane region. Start near 60.
- `persp_top_half_pct`: half-width of the source trapezoid at its top. Start near 15.
- `persp_bottom_margin_pct`: source trapezoid margin at the image bottom. Start near 16.
- `bird_dst_margin_pct`: destination margin; this defines nominal lane width in bird's-eye view. Start near 22.
- `sliding_windows`: number of vertical windows. Start near 10.
- `window_margin_pct`: lateral search radius per window. Start near 7-8.
- `min_lane_pixels`: minimum support before fitting a boundary. Start near 60.
- `bird_width_tol_pct`: accepted variation from nominal lane width. Start near 34.
- `temporal_alpha_pct`: new-frame weight in temporal smoothing. Start near 62.

Do not tune `bird_dst_margin_pct` independently of the three source-trapezoid
parameters. Together they represent the hard-coded camera/ground-plane mapping.

## Commands

Interactive tuning:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\visualize_yolop_lane_offset.py `
  --dataset practice --trip T01-Sample --mode tuner
```

Single-frame validation:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\visualize_yolop_lane_offset.py `
  --dataset practice --trip T01-Sample --frame 300 --mode frame
```

Video export:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\visualize_yolop_lane_offset.py `
  --dataset practice --trip T01-Sample --mode video --fps 20
```

Regression tests:

```powershell
uv run python -m unittest discover -s tests -v
```

## Validation performed

YOLOP masks were generated and inspected at five evenly distributed T01 frames:

- `000000`
- `000150`
- `000300`
- `000449`
- `000599`

Validation images are under:

- `artifacts/roadface/carnd_lane_offset_validation`
- `artifacts/roadface/carnd_lane_offset_validation_v2`

Frame `000150` exposed a dense-curb failure. Before the ego-corridor check, the
reported offset was `+7.05 m`. After selecting the boundary by geometric
consistency with the ego center, the result became `-0.42 m`.

Automated tests cover:

- disconnected fragments with no bottom mask;
- one visible curved boundary with the opposite side inferred;
- a dense curb competing with the ego-lane boundary.

This is qualitative validation because the practice dataset does not provide a
verified lane-center/offset ground truth for these frames. Quantitative accuracy
requires manually annotated lane boundaries or simulator lane-center ground
truth.
