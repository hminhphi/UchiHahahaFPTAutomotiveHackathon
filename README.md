# FleetIQ Guardian

FleetIQ Guardian is a remote driver-intelligence and collision-risk platform built for the FPT Automotive Hackathon 2026 by team UchiHahaha.

The project combines road-facing stereo cameras, cabin-camera signals, depth, calibration, KITTI annotations, and vehicle telemetry to answer:

1. Which driver, vehicle, or trip is currently risky?
2. Why is the risk high, with timestamped visual evidence?
3. What coaching or operational action should follow?

The submission targets **Challenge #3: Driver Intelligence Platform**, with safe-driving scoring and vision-based collision-risk monitoring as its core modules.

## Main Capabilities

- Synchronized visualization of `image_2`, `image_3`, driver camera, depth, calibration, labels, and telemetry.
- Open-vocabulary relabeling with NVIDIA LocateAnything-3B.
- KITTI-compatible custom labels for cars, buses, long vehicles, motorcycles, cyclists, and pedestrians.
- Object tracking, depth-based distance estimation, relative speed, TTC, and near-miss detection.
- Road-plane and lane-corridor experiments for filtering relevant obstacles.
- Trip-level event fusion, explainable risk scoring, and dashboard-ready outputs.

## Repository Layout

```text
apps/                    Web and CarSky user interfaces
services/                Deployable inference and event workers
packages/                Shared contracts and dataset libraries
ml/training/roadface/    Relabeling, preparation, training, and evaluation
ml/notebooks/            Dataset inventory and synchronization experiments
tools/visualization/     Trip player and road-facing audit tools
tools/dataset/           Notebook and dataset utilities
tools/presentation/      Proposal deck generation
tests/                   Cross-project architecture tests
```

Datasets, model weights, generated labels, training runs, videos, and extracted artifacts are intentionally excluded from Git.

## Requirements

- Windows PowerShell
- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- NVIDIA GPU recommended for model inference

Create the environment:

```powershell
uv sync --all-packages
```

Install the CUDA and road-facing perception extras:

```powershell
uv sync --all-packages --extra cu130 --extra models
uv run --package fleetiq-training-roadface python -m fleetiq_training_roadface.check_environment --probe-cuda
```

## Expected Dataset Layout

The data is not committed. Place the organizer-provided dataset under:

```text
data/
  Practice_Dataset/
    Practice_Dataset/
      T01-Sample/
        T01-Sample.json.gz
        driver/
        kitti/
          image_2/
          image_3/
          depth/
          calib/
          label_2/
  Hackathon_Dataset_Redacted/
    Hackathon_Dataset_Redacted/
      T01d/
      ...
```

## Synchronized Dataset Player

List trips and open the synchronized driving view:

```powershell
uv run --package fleetiq-training-roadface python tools\visualization\trip_player.py --list-trips
uv run --package fleetiq-training-roadface python tools\visualization\trip_player.py --trip T01-Sample --mode window
```

Render one frame:

```powershell
uv run --package fleetiq-training-roadface python tools\visualization\trip_player.py --trip T06-Sample --mode frame --frame 100
```

## LocateAnything Relabeling

Relabel the Practice Dataset into each trip's `kitti/label2_custom` directory:

```powershell
uv run --package fleetiq-training-roadface --extra models fleetiq-label-roadface --dataset practice --generation-mode slow --continue-on-error
```

Check progress:

```powershell
uv run --package fleetiq-training-roadface python tools\visualization\roadface\check_locateanything_progress.py --dataset practice
```

Visualize custom bounding boxes:

```powershell
uv run --package fleetiq-training-roadface python tools\visualization\roadface\visualize_kitti_labels.py --dataset practice --trip T06-Sample --label-dir-name label2_custom --start 0 --end 599 --stride 120 --max-frames 5 --mode contact-sheet
```

The original `label_2` directory is never overwritten. LocateAnything raw responses are stored beside generated labels for auditing.

## Road-Facing TTC Pipeline

Run detection, depth, lane filtering, tracking, relative-speed estimation, and TTC:

```powershell
uv run --package fleetiq-roadface fleetiq-roadface --dataset-root data\Practice_Dataset\Practice_Dataset --trip T06-Sample --detection-source labels_custom --lane-method plane --depth-source ground_truth --visualize
```

Generated CSV, JSONL, frames, and videos are written under `artifacts/` and remain outside Git.

## Tests

```powershell
uv run pytest
```

## Documentation

- [System architecture](docs/architecture.md)
- [Road-facing perception pipeline](docs/ROADFACE_PIPELINE.md)
- [LocateAnything relabeling](docs/LOCATEANYTHING_RELABELING.md)
- [Risk pipeline architecture](docs/RISK_PIPELINE_ARCHITECTURE.md)
- [Full proposal plan](docs/FULL_VERTICAL_PROPOSAL_PLAN.md)

## Model License Note

LocateAnything-3B is loaded from a pinned NVIDIA model revision with `trust_remote_code=True`. NVIDIA's released weights are licensed for research and non-commercial development; verify license compatibility before any commercial deployment.
