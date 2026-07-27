# Lane detection: AI mask + road-plane geometry

## Why the previous approach was insufficient

The earlier lane demo mixed two separate problems:

- Detecting 2D lane/road evidence in the image.
- Estimating metric lane offset in the vehicle/camera coordinate system.

Drawing two image-space lines is not enough for collision-risk filtering. A correct implementation should first obtain road/lane evidence, then project that evidence onto a road plane using calibration and depth, and only then estimate offset/heading in meters.

## Research-backed direction

### Multi-task driving perception

These models are the most practical for this hackathon because they output the perception heads we need from a front camera:

- YOLOP: traffic object detection, drivable-area segmentation and lane detection in one network. Official repo: https://github.com/hustvl/YOLOP
- HybridNets: object detection, drivable area and lane line detection with stronger lane accuracy than YOLOP in its paper. Paper: https://huggingface.co/papers/2203.09035
- DLT-Net: older but relevant multi-task formulation for drivable areas, lane lines and traffic objects. Paper page: https://publications.ri.cmu.edu/dlt-net-joint-detection-of-drivable-areas-lane-lines-and-traffic-objects-2

Recommended hackathon use:

- Use YOLOP/HybridNets-style models for `road_mask` and `lane_mask`.
- Keep YOLO11/RT-DETR for object boxes if it performs better on this synthetic dataset.
- Fuse the masks with depth/calibration instead of trusting 2D lane pixels directly.

### Dedicated 2D lane detection

Dedicated lane detectors are better for lane markings than generic semantic segmentation:

- CLRNet uses cross-layer refinement to combine high-level lane semantics with low-level localization detail.
- UFLD/UFLD-v2 focuses on efficient row-anchor lane localization.
- LaneATT and CondLaneNet are strong alternatives when the task is specifically 2D lane-marking detection.

Recommended hackathon use:

- Treat dedicated lane detectors as optional lane-line evidence.
- Do not use their raw 2D lines directly for TTC gating.
- Lift their lane pixels/points to the road plane and compute metric lane center/offset.

### 3D lane detection

3D lane papers are closest to the mathematically correct target, but heavier to integrate:

- 3D-LaneNet predicts 3D lane layout directly and uses an in-network IPM idea.
- PersFormer/OpenLane uses camera-parameter-guided perspective transformation for 3D lane detection.
- LATR reports stronger OpenLane results but has a larger integration footprint.

Recommended hackathon use:

- Do not make full 3D lane detection the MVP unless the team already has weights and time.
- Borrow the geometry principle: output lane/corridor in camera/ground coordinates, not just pixels.

### Road-plane fitting and IPM

Plane-based geometry is the missing piece:

- Ground plane fitting with RANSAC is a standard robust way to estimate the dominant road plane from stereo/depth points.
- IPM/back-projection maps image evidence onto the road plane, where lane width, lateral offset and heading are measured in meters.
- For this dataset, GT depth and KITTI intrinsics make plane fitting much more reliable than pure monocular lane-line geometry.

Implementation now added:

- `scripts/roadface/roadface_lib.py`
  - `fit_road_plane_ransac`
  - `intersect_pixels_with_plane`
  - `estimate_plane_lane`
  - `plane_lane_masks_from_centerline`
- `scripts/roadface/demo_plane_lane_offset.py`
  - `--mask-source classical`: fallback road ROI only, for geometry smoke tests.
  - `--mask-source transformers`: Hugging Face segmentation model path.
  - `--mask-source files`: consume external AI mask PNGs from YOLOP/HybridNets/CLRNet/PersFormer adapters.

## Correct project contract

The robust architecture should be:

```text
image_2/image_3
  -> AI road/lane segmentation
  -> depth from GT / stereo / monocular depth
  -> camera calibration
  -> RANSAC road-plane fit
  -> back-project road/lane pixels to plane
  -> fit ego-lane centerline in X-Z metric space
  -> build ego-lane risk corridor/prism
  -> filter objects
  -> distance, relative speed, TTC
```

## Recommended model options

MVP:

- Use `HybridNets` or `YOLOP` to produce `road_mask` and `lane_mask`.
- Use existing YOLO11/RT-DETR object detector for vehicles/pedestrians/cyclists.
- Use GT depth when available; use stereo or monocular depth as fallback.
- Compute lane offset from `estimate_plane_lane`, not from 2D lines.

Accuracy-first stretch:

- Use a dedicated lane model such as CLRNet/CondLaneNet for lane-line evidence.
- Use a stronger semantic segmentation model such as SegFormer/Mask2Former for road/drivable mask.
- Keep road-plane geometry as the single source of metric truth.

Research stretch:

- Evaluate PersFormer/LATR/OpenLane-style 3D lane detectors if pretrained weights and integration time are available.

## Important limitation

If the model only sees one front camera image, lane offset can be visually plausible but geometrically fragile unless supported by calibration/depth/plane fitting. For collision risk, the correct demo claim is:

> We estimate an ego-lane risk corridor on the fitted road plane, then use it to decide which objects are relevant for distance and TTC.

This is stronger and safer than claiming production-grade lane keeping from two image-space lines.
