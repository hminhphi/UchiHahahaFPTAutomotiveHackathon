# FleetIQ road-facing perception pipeline

This folder builds the road-camera side of the hackathon proposal:

- object position per frame
- projected 2D boxes and available 3D pose
- lane and road masks
- lane offset estimate
- distance estimate per tracked object
- frame-to-frame relative speed and TTC
- visual evidence video/frame outputs

## Data split

Use practice trips for supervised development because they keep full ground truth:

- Train: `T01-Sample` to `T04-Sample`
- Validation: `T05-Sample`
- Test: `T06-Sample`
- Demo/submission inference: `T01d` to `T10d`

The redacted trips zero out KITTI `location` and many GT fields. Treat them as inference/demo data, not supervised 3D training data.

## Lane-first target policy

The KITTI labels in this dataset are not clean full-scene object detection labels. They behave more like front-risk targets chosen by the organizer: many visible vehicles are unlabeled, and some projected 3D boxes do not tightly match visible silhouettes. For collision risk, this is acceptable only if we treat labels as "objects relevant to the ego lane", not as exhaustive annotations.

The current exporter and inference pipeline therefore use a lane-first filter by default:

- Detect the road/lane floor corridor.
- Extrude that corridor vertically into a risk prism.
- Keep a labeled or detected object only when its 3D lateral position is inside the ego-lane width, or its bbox foot point is supported by the corridor.
- Use `--no-lane-filter` only for debugging full noisy labels.

## Quick commands

```powershell
# Lane corridor and lane offset demo inspired by the MMAE lane paper.
.venv\Scripts\python.exe scripts\roadface\demo_lane_mmae_offset.py --dataset practice --trip T01-Sample --mode frame --frame 324
.venv\Scripts\python.exe scripts\roadface\demo_lane_mmae_offset.py --dataset practice --trip T06-Sample --mode video --start 80 --end 130

# Preferred geometry path: AI/external road mask -> road plane -> metric lane corridor.
.venv\Scripts\python.exe scripts\roadface\demo_plane_lane_offset.py --dataset practice --trip T06-Sample --frame 100 --mask-source classical
.venv\Scripts\python.exe scripts\roadface\demo_plane_lane_offset.py --dataset practice --trip T06-Sample --frame 100 --mask-source transformers --seg-model nvidia/segformer-b0-finetuned-cityscapes-1024-1024
.venv\Scripts\python.exe scripts\roadface\demo_plane_lane_offset.py --dataset practice --trip T06-Sample --frame 100 --mask-source files --road-mask-dir artifacts\roadface\ai_masks\road --lane-mask-dir artifacts\roadface\ai_masks\lane

# Audit Model 1/2/3 decisions before trusting a lane overlay.
.venv\Scripts\python.exe scripts\roadface\audit_lane_models.py --dataset practice --trip T06-Sample --frames 100,127

# Regression audit: 6 practice trips x 5 evenly sampled frames.
.venv\Scripts\python.exe scripts\roadface\audit_plane_lane.py --dataset practice --frames-per-trip 5 --output-dir artifacts\roadface\plane_lane_audit

# Minimal offline smoke test: labels + GT depth on one practice trip.
.venv\Scripts\python.exe scripts\roadface\run_roadface_pipeline.py --dataset practice --trip T06-Sample --start 20 --end 80 --visualize video

# Preferred collision-risk run: plane-based ego-lane corridor + labels/GT depth.
.venv\Scripts\python.exe scripts\roadface\run_roadface_pipeline.py --dataset practice --trip T06-Sample --start 100 --end 160 --lane-method plane --detector labels --depth-source gt --visualize video

# Export projected KITTI 3D boxes to YOLO format.
.venv\Scripts\python.exe scripts\roadface\prepare_roadface_dataset.py

# Export the older noisy version for comparison only.
.venv\Scripts\python.exe scripts\roadface\prepare_roadface_dataset.py --no-lane-filter --output-dir artifacts\roadface\yolo_dataset_noisy

# Install PyTorch CUDA through the project config.
uv lock --extra cu130 --extra roadface --upgrade-package torch --upgrade-package torchvision
uv sync --extra cu130 --extra roadface

# Sanity-check that uv run sees the CUDA build, not the PyPI CPU build.
uv run --extra cu130 --extra roadface python scripts\roadface\check_roadface_env.py
uv run --extra cu130 --extra roadface python scripts\roadface\check_roadface_env.py --probe-cuda

# Safe RTX 5060 Ti 16GB profile.
uv run --extra cu130 --extra roadface python scripts\roadface\train_roadface_models.py --prepare --model yolo11l.pt --epochs 80 --imgsz 768 --batch 2 --device 0 --name yolo11l_roadface_768

# Higher accuracy, higher VRAM. Use this only after the safe profile runs.
uv run --extra cu130 --extra roadface python scripts\roadface\train_roadface_models.py --model yolo11x.pt --epochs 80 --imgsz 640 --batch 1 --device 0 --name yolo11x_roadface_640

# Transformer detector comparison.
uv run --extra cu130 --extra roadface python scripts\roadface\train_roadface_models.py --model rtdetr-l.pt --epochs 80 --imgsz 640 --batch 1 --device 0 --name rtdetr_l_roadface_640

# Run trained detector plus stereo depth on redacted/demo trips.
uv run --extra cu130 --extra roadface python scripts\roadface\run_roadface_pipeline.py --dataset redacted --detector yolo --yolo-weights artifacts/roadface/train_runs/yolo_roadface/weights/best.pt --depth-source stereo --visualize video

# Compare outputs on the practice test trip.
uv run --extra cu130 --extra roadface python scripts\roadface\evaluate_roadface_outputs.py --trip T06-Sample
```

## Recommended model ladder

Detector:

- `yolo11x.pt` or `yolo11l.pt` through Ultralytics for a strong fine-tuned detector baseline.
- If time allows, also try transformer detectors such as RT-DETR variants through the same Ultralytics ecosystem, but keep YOLO as the dependable training path.

Depth:

- `gt`: use dataset depth keyframes for upper-bound validation and the cleanest demo evidence.
- `stereo`: use `image_2` + `image_3` + calibration for redacted trips when labels are zeroed.
- `transformers:depth-anything/Depth-Anything-V2-Metric-Outdoor-Large-hf` if available in cache/HF. This is the best first monocular metric-depth baseline for outdoor driving.
- `transformers:Intel/zoedepth-nyu-kitti` as a second metric-depth baseline.
- Lotus Depth can be added as an experimental provider, but it is better treated as a separate finetune experiment because many Lotus releases use custom diffusion code rather than the standard `transformers` depth pipeline.

## Output contract

Each trip writes:

- `artifacts/roadface/predictions/<trip>_roadface.csv`
- `artifacts/roadface/predictions/<trip>_roadface.jsonl`
- optional rendered `.mp4` or `.png`

Important columns:

- `track_id`
- `object_type`
- `bbox_x1`, `bbox_y1`, `bbox_x2`, `bbox_y2`
- `x_m`, `z_m`, `distance_m`
- `relative_speed_mps`
- `ttc_s`
- `lane_offset_m`
- `detector_source`
- `distance_source`

## Notes for the hackathon demo

For the cleanest 2 to 3 week execution, use three modes:

- Oracle/dev mode: `--detector labels --depth-source gt` on practice trips to validate math and visual story.
- Realistic mode: `--detector yolo --depth-source stereo` on redacted trips.
- Research mode: compare `stereo`, Depth Anything V2 metric, ZoeDepth, and Lotus Depth on `T06-Sample`.

Do not claim monocular depth alone is safety-grade. The safer product story is multi-cue: detector tracking + stereo/depth ROI + calibration + temporal smoothing + TTC confidence.
