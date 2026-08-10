<!-- prettier-ignore -->
<div align="center">

# FleetIQ Guardian

**Remote driver intelligence and collision-risk platform for the FPT Automotive Hackathon 2026**

![Python](https://img.shields.io/badge/Python-3.12-3776ab?style=flat-square&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-workspace-222?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-dashboard-000?style=flat-square&logo=nextdotjs)
![FastAPI](https://img.shields.io/badge/FastAPI-control_plane-009688?style=flat-square&logo=fastapi&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-ECS_EC2_%2B_SageMaker-ff9900?style=flat-square&logo=amazonaws&logoColor=white)

[Overview](#overview) - [Quick Start](#quick-start) - [Dataset](#dataset) - [Development](#development) - [Deployment](#deployment) - [Docs](#documentation)

</div>

## Overview

FleetIQ Guardian turns road-facing stereo cameras, driver camera signals, depth
maps, calibration files, labels, and vehicle telemetry into a fleet safety
dashboard. The judge-facing story is simple: identify the risky trip, explain
why it is risky, show timestamped visual evidence, and produce a bounded
coaching action.

The submission targets **Challenge #3: Driver Intelligence Platform**. Challenge
#1 safe-driving scoring and Challenge #2 collision-risk/TTC detection are built
as core engines underneath the product.

### What It Does

| Capability | Output |
| --- | --- |
| Road-facing perception | Objects, lane/road mask, lane offset, depth, distance, tracking, TTC |
| Driver monitoring | Driver state events for attention, drowsiness, and distraction workflows |
| Telemetry analytics | Speeding, harsh brake, fast corner, acceleration, route trajectory coloured from blue (0 km/h) to red (100 km/h) |
| Fusion and scoring | Unified risk events, trip score, explanations, coaching recommendations |
| Fleet dashboard | Driver ranking, trip drill-down, timelines, evidence viewer, report panel |
| CarSky HMI | Android Automotive coaching acknowledgement path for IVI demo |

## Architecture

```text
Road/driver cameras --WSS--> FastAPI control plane ----HTTP/WSS----> Next.js dashboard
Vehicle telemetry -----MQTT--> Event gateway ----------MQTT--------> Fusion/scoring
Frames and features ---------> Roadface + DMS workers --HTTPS------> SageMaker endpoints
Coaching command ------HTTPS--> CarSky bridge ---------------------> Android Automotive HMI
```

> [!NOTE]
> Local development uses Docker Compose for the API, dashboard, MQTT, database,
> cache, model mock, and CarSky bridge. The intended cloud shape runs
> frontend/backend on **ECS EC2** and model inference on **SageMaker**.

Core protocols:

| Protocol | Used for |
| --- | --- |
| HTTP/HTTPS | Health checks, trip queries, jobs, reports, coaching delivery |
| WebSocket/WSS | Camera frame ingress and latest trip-state streams |
| MQTT | Telemetry events, risk events, coaching commands, acknowledgements |
| JSONL | Bounded offline worker input/output during hackathon development |

See [system architecture](docs/architecture/system.md), [repository
boundaries](docs/architecture/repository.md), and [protocol contracts](docs/protocols/README.md).

## Repository Map

```text
apps/          Next.js web app, FastAPI API, CarSky Android HMI and bridge
services/      Roadface, DMS, fusion, coaching, and MQTT gateway workers
packages/      Shared contracts, dataset kit, model clients, observability
ml/            Training jobs, notebooks, SageMaker handlers, model configs
tools/         Dataset utilities, visualization tools, presentation helpers
infra/         Docker Compose, Docker images, AWS CDK
docs/          Architecture, runbooks, proposal, reports, references
research/      Authored research notes; raw papers/clones stay local
data/          Local organizer datasets, ignored by git
artifacts/     Local generated outputs and model files, ignored by git
```

Each top-level work area has its own README with ownership, inputs, outputs, and
validation notes.

## Prerequisites

- Python `3.12`
- [uv](https://docs.astral.sh/uv/)
- Node.js `22`
- pnpm `11`
- Docker Desktop for Compose demos
- NVIDIA GPU plus CUDA PyTorch only for heavyweight local perception
- Optional Android SDK/Gradle for local CarSky HMI work
- Optional AWS credentials and bootstrapped CDK account for cloud deployment

Install dependencies:

```powershell
uv sync --all-packages --group dev
pnpm install --frozen-lockfile
```

Check the road-facing Python/CUDA environment when needed:

```powershell
uv run --package fleetiq-training-roadface python -m fleetiq_training_roadface.check_environment --probe-cuda
```

## Quick Start

### 1. Run The Dashboard Locally

Start the API:

```powershell
$env:FLEETIQ_TESTING = "true"; uv run --package fleetiq-api uvicorn fleetiq_api.main:create_app --factory --host 0.0.0.0 --port 8000
```

Start the web app in another terminal:

```powershell
pnpm --filter @fleetiq/web dev
```

Open:

- Dashboard: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>

The dashboard has fixture fallback data, so the product walkthrough still works
before live perception output is available.

To run a local historical replay without Docker/MinIO, enable the filesystem
backend explicitly in the API terminal:

```powershell
$env:FLEETIQ_TESTING = "true"
$env:FLEETIQ_REPLAY_ENABLED = "true"
$env:FLEETIQ_MEDIA_BACKEND = "filesystem"
$env:FLEETIQ_DATASET_ROOT = "data/Practice_Dataset/Practice_Dataset"
uv run --package fleetiq-api uvicorn fleetiq_api.main:create_app --factory --host 0.0.0.0 --port 8000
```

### 2. Run The Full Local Stack

Start Docker Desktop, then run:

```powershell
Copy-Item .env.example .env
docker compose --profile full up --build
```

If port `3000` is already in use, set `FLEETIQ_WEB_PORT=3001` in `.env` and
open <http://localhost:3001> instead.

Run the protocol smoke test in another terminal:

```powershell
uv run --group dev python infra/compose/smoke_test.py
```

Expected result: `8/8` covering API readiness, telemetry MQTT, model mock,
risk MQTT, producer camera WebSocket framing, ordered historical replay,
fleet/trajectory telemetry, and CarSky acknowledgement.

The first start mirrors the local Practice Dataset into MinIO and can take a
few minutes. Once `minio-seed` reports success, open
`http://localhost:3000/trips/T01-Sample`: the road-facing video replays from
the `fleetiq-demo` bucket instead of a one-frame fixture. MinIO is available at
`http://localhost:9001`; production uses the same S3-compatible interface with
an AWS S3 bucket. The Trip Detail route moves its `NOW` vehicle marker and all
telemetry cards from the binary replay frame index, not from a separate timer.

Stop the stack:

```powershell
docker compose --profile full down
```

### 3. Run The Practice Dataset Viewer

List trips:

```powershell
uv run --package fleetiq-training-roadface python tools/visualization/trip_player.py --list-trips
```

Open a synchronized road/driver/stereo/depth/telemetry viewer:

```powershell
uv run --package fleetiq-training-roadface python tools/visualization/trip_player.py --trip T06-Sample --mode window
```

Run the road-facing lane/depth/tracking/TTC pipeline:

```powershell
uv run --package fleetiq-roadface fleetiq-roadface `
  --dataset-root data/Practice_Dataset/Practice_Dataset `
  --trip T06-Sample `
  --detection-source labels_custom `
  --lane-method plane `
  --depth-source ground_truth `
  --visualize
```

## Dataset

Datasets are local-only and must not be committed. Put organizer data under:

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
          label2_custom/
  Hackathon_Dataset_Redacted/
    Hackathon_Dataset_Redacted/
      T01d/
      ...
```

Useful signals already identified in the Practice Dataset:

| Signal | Use |
| --- | --- |
| `kitti/image_2`, `kitti/image_3` | Rectified stereo road cameras |
| `kitti/depth` | Ground-truth depth at lower frequency for validation/fallback |
| `kitti/calib` | `fx=320`, `fy=320`, `cx=320`, `cy=180`, stereo baseline `0.30 m` |
| Trip JSON telemetry | Speed, acceleration, yaw/pitch/roll, location, targets, TTC, risk |
| `driver/` frames | In-cabin DMS evidence stream |
| `kitti/label_2` and `label2_custom` | Original and relabeled road-object annotations |

Read the full dataset audit in [docs/DATASET_SIGNAL_AUDIT.md](docs/DATASET_SIGNAL_AUDIT.md).

## Perception Workflow

Relabel Practice Dataset road objects into `kitti/label2_custom`:

```powershell
uv run --package fleetiq-training-roadface --extra models fleetiq-label-roadface --dataset practice --generation-mode slow --continue-on-error
```

Prepare, train, and evaluate road-facing models:

```powershell
uv run --package fleetiq-training-roadface fleetiq-prepare-roadface
uv run --package fleetiq-training-roadface --extra models fleetiq-train-roadface
uv run --package fleetiq-training-roadface fleetiq-evaluate-roadface
```

Run bounded worker entrypoints:

```powershell
uv run --package fleetiq-dms-worker fleetiq-dms-worker
uv run --package fleetiq-fusion-worker fleetiq-fusion-worker
uv run --package fleetiq-coaching-worker fleetiq-coaching-worker
uv run --package fleetiq-event-gateway fleetiq-event-gateway
```

Roadface, DMS, fusion, and coaching workers are currently CLI/JSONL jobs. The
event gateway is the long-running MQTT daemon.

## Development

Run the main quality gates before pushing shared work:

```powershell
uv lock --check
uv run ruff check apps packages services ml infra tools
uv run python -m pytest -v
pnpm --filter @fleetiq/web lint
pnpm --filter @fleetiq/web typecheck
pnpm --filter @fleetiq/web test
pnpm --filter @fleetiq/web build
docker compose --profile full config
uv run --group dev python infra/compose/smoke_test.py
```

> [!IMPORTANT]
> Cross-service payloads belong in `packages/contracts`. Do not import another
> service's internal modules to share event shapes or API models.

### Command Migration

| Old location | Current command |
| --- | --- |
| `scripts/roadface/run_roadface_pipeline.py` | `uv run --package fleetiq-roadface fleetiq-roadface` |
| `scripts/roadface/prepare_roadface_dataset.py` | `uv run --package fleetiq-training-roadface fleetiq-prepare-roadface` |
| `scripts/roadface/train_roadface_models.py` | `uv run --package fleetiq-training-roadface fleetiq-train-roadface` |
| `scripts/roadface/evaluate_roadface_outputs.py` | `uv run --package fleetiq-training-roadface fleetiq-evaluate-roadface` |
| `scripts/roadface/relabel_locateanything.py` | `uv run --package fleetiq-training-roadface --extra models fleetiq-label-roadface` |
| `scripts/render_trip_dashboard.py` | `tools/visualization/trip_player.py` |
| `scripts/generate_dataset_notebooks.py` | `tools/dataset/generate_notebooks.py` |
| `scripts/pptx/` | `tools/presentation/` |

## Deployment

Local profiles are documented in [infra/compose/README.md](infra/compose/README.md):

| Profile | Starts |
| --- | --- |
| `core` | PostgreSQL, Redis, MQTT, API, web, event gateway |
| `perception` | `core` plus local SageMaker-compatible model mock |
| `full` | `perception` plus CarSky bridge |

Cloud deployment is designed around:

| Layer | Target |
| --- | --- |
| Frontend and API | ECS EC2 behind an HTTPS load balancer |
| Detector, depth, lane, DMS inference | SageMaker endpoints |
| Telemetry and vehicle events | AWS IoT Core/MQTT |
| Runtime artifacts | S3 |
| Secrets | AWS Secrets Manager |

See [AWS deploy runbook](docs/runbooks/aws-deploy.md) and [CarSky deploy
runbook](docs/runbooks/carsky-deploy.md).

## Final Release

The `v1.0.0` reviewer handoff separates source, local runtime artifacts, and
organizer data. Follow [the final release runbook](docs/runbooks/final-release.md)
to restore the evidence package and run the Docker dashboard. Build the local
runtime archive with `./create_release_package.ps1`; do not distribute organizer
data publicly without approval.

## Documentation

- [Architecture](docs/architecture/README.md)
- [Protocols](docs/protocols/README.md)
- [Runbooks](docs/runbooks/README.md)
- [CI validation](docs/runbooks/ci-validation.md)
- [Proposal assets](docs/proposal/README.md)
- [Dataset signal audit](docs/DATASET_SIGNAL_AUDIT.md)
- [Demo guide and E2E acceptance](docs/demo/README.md)
- [Road-facing training](ml/training/roadface/README.md)
- [Visualization tools](tools/visualization/README.md)

## Team Ownership

| Member | GitHub | Primary boundary |
| --- | --- | --- |
| Phi | `hminhphi` | Road-facing camera, automotive integration, perception delivery |
| Trung | `hoangtrung1801` | In-cabin DMS and driver-state CV |
| Dung | `VKUNeMo` | AI agent/NLP and coaching intelligence |
| Kha | `khaphan11` | CV/AI-ML training, depth, detection, lane evaluation |
| Tu | `four2k3` | AI agent, backend/software integration, dashboard support |

## Local Artifacts And Secrets

Commit source, tests, lightweight configs, authored docs, and approved proposal
artifacts. Keep these local-only:

```text
data/
artifacts/models/
artifacts/training/
artifacts/predictions/
artifacts/renders/
artifacts/reports/
artifacts/research-extracts/
research/papers/raw/
research/third-party/
.env
```

LocateAnything-3B and similar research models may have non-commercial or
research-only license terms. Verify every model and dataset license before any
commercial claim.
