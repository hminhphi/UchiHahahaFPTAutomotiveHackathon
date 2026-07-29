# FleetIQ Guardian

FleetIQ Guardian is team UchiHahaha's remote driver-intelligence and
collision-risk platform for the FPT Automotive Hackathon 2026. In 30 seconds:
it synchronizes stereo road cameras, driver camera, depth, calibration, labels,
and vehicle telemetry; detects short TTC, lane/handling risk, and driver state;
then shows fleet managers the trip score, timestamped evidence, explanation,
and a safety-bounded coaching action.

The submission targets **Challenge #3: Driver Intelligence Platform**.
Challenge #1 scoring and Challenge #2 collision risk are the two core engines.

## Architecture

```text
Road/driver camera --WSS--> FastAPI control plane --> Next.js fleet dashboard
Telemetry/risk ------MQTT--> event gateway -------> fusion/scoring/coaching
Frames --------------------> roadface + DMS ------> SageMaker endpoints
Coaching command ----HTTPS--> CarSky bridge ------> Android Automotive HMI
```

- HTTP/HTTPS: health, fleet/trip queries, jobs, reports, and coaching delivery
- WebSocket/WSS: bounded camera frames and latest-state dashboard streams
- MQTT: versioned telemetry, risk, coaching command, and acknowledgement events
- Local deployment: Docker Compose `core`, `perception`, and `full` profiles
- AWS deployment: web/API on ECS EC2; detector/depth/lane/DMS on SageMaker

See [system architecture](docs/architecture/system.md),
[repository boundaries](docs/architecture/repository.md), and
[versioned protocols](docs/protocols/README.md).

## Repository

```text
apps/          Next.js dashboard, FastAPI API, CarSky Android HMI
services/      MQTT, roadface, DMS, fusion, and coaching workers
packages/      Contracts, dataset kit, model clients, observability
ml/            Training, SageMaker handlers, notebooks, model configs
tools/         Dataset, visualization, and presentation entrypoints
infra/         Docker Compose, reusable images, AWS CDK
docs/          Architecture, proposal, references, reports, runbooks
research/      Authored notes; ignored raw papers and third-party clones
data/          Ignored organizer datasets
artifacts/     Ignored models, runs, predictions, renders, and reports
```

## Prerequisites

- Python `3.12`
- [uv](https://docs.astral.sh/uv/)
- Node.js `22` and pnpm `11`
- Docker Desktop for local multi-service profiles
- NVIDIA GPU and compatible PyTorch only for heavyweight local inference
- Optional: Android SDK/Gradle for local HMI build
- Optional: AWS credentials and a bootstrapped CDK account for cloud deployment

Install the Python workspace and frontend dependencies:

```powershell
uv sync --all-packages --group dev
pnpm install --frozen-lockfile
```

Validate CUDA only when needed:

```powershell
uv run --package fleetiq-training-roadface python -m fleetiq_training_roadface.check_environment --probe-cuda
```

## Demo Quick Start

### Dashboard in two terminals

Start the API in terminal 1:

```powershell
$env:FLEETIQ_TESTING = "true"
uv run --package fleetiq-api uvicorn fleetiq_api.main:create_app --factory --host 0.0.0.0 --port 8000
```

Start the Next.js dashboard in terminal 2:

```powershell
pnpm --filter @fleetiq/web dev
```

Open:

- Fleet dashboard: <http://localhost:3000>
- FastAPI Swagger: <http://localhost:8000/docs>

The dashboard falls back to bundled fixture trips when the API has no analyzed
trips, so the product story remains demonstrable before running perception.

### Full end-to-end demo

Start Docker Desktop, then bring up API, dashboard, PostgreSQL, Redis, MQTT,
the SageMaker-compatible model mock, and the CarSky bridge:

```powershell
Copy-Item .env.example .env
docker compose --profile full up --build
```

Run the six-protocol smoke test in another terminal:

```powershell
uv run --group dev python infra/compose/smoke_test.py
```

The expected result is `6/6`: API readiness, telemetry MQTT, mock inference,
risk MQTT, binary camera WebSocket framing, and CarSky acknowledgement. Open
<http://localhost:3000> for the dashboard and stop the stack without deleting
volumes when the demo finishes:

```powershell
docker compose --profile full down
```

### Practice Dataset camera demo

List available trips and launch the synchronized road/driver/stereo/depth view:

```powershell
uv run --package fleetiq-training-roadface python tools/visualization/trip_player.py --list-trips
uv run --package fleetiq-training-roadface python tools/visualization/trip_player.py --trip T06-Sample --mode window
```

Run the lane, depth, tracking, relative-speed, and TTC pipeline on one trip:

```powershell
uv run --package fleetiq-roadface fleetiq-roadface `
  --dataset-root data/Practice_Dataset/Practice_Dataset `
  --trip T06-Sample `
  --detection-source labels_custom `
  --lane-method plane `
  --depth-source ground_truth `
  --visualize
```

Recommended judge flow: fleet overview, risky trip drill-down, synchronized TTC
and driver-state timeline, camera evidence, score explanation, then a
safety-bounded coaching acknowledgement from CarSky.

## Dataset

Datasets are never committed. Place organizer data under:

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

List trips or render synchronized road/driver/stereo/depth/telemetry views:

```powershell
uv run --package fleetiq-training-roadface python tools/visualization/trip_player.py --list-trips
uv run --package fleetiq-training-roadface python tools/visualization/trip_player.py --trip T06-Sample --mode frame --frame 100
```

## Perception Workflow

Relabel only `data/Practice_Dataset` into `kitti/label2_custom`:

```powershell
uv run --package fleetiq-training-roadface --extra models fleetiq-label-roadface --dataset practice --generation-mode slow --continue-on-error
```

Prepare, train, and evaluate road-facing models:

```powershell
uv run --package fleetiq-training-roadface fleetiq-prepare-roadface
uv run --package fleetiq-training-roadface --extra models fleetiq-train-roadface
uv run --package fleetiq-training-roadface fleetiq-evaluate-roadface
```

Run the road-facing TTC pipeline:

```powershell
uv run --package fleetiq-roadface fleetiq-roadface --dataset-root data/Practice_Dataset/Practice_Dataset --trip T06-Sample --detection-source labels_custom --lane-method plane --depth-source ground_truth --visualize
```

Run worker JSONL entrypoints:

```powershell
uv run --package fleetiq-dms-worker fleetiq-dms-worker
uv run --package fleetiq-fusion-worker fleetiq-fusion-worker
uv run --package fleetiq-coaching-worker fleetiq-coaching-worker
uv run --package fleetiq-event-gateway fleetiq-event-gateway
```

Roadface, DMS, fusion, and coaching workers are currently bounded CLI/JSONL
jobs. Only the event gateway is a long-running MQTT daemon.

## Command Migration

| Removed location/command | Replacement |
| --- | --- |
| `scripts/roadface/run_roadface_pipeline.py` | `uv run --package fleetiq-roadface fleetiq-roadface` |
| `scripts/roadface/prepare_roadface_dataset.py` | `uv run --package fleetiq-training-roadface fleetiq-prepare-roadface` |
| `scripts/roadface/train_roadface_models.py` | `uv run --package fleetiq-training-roadface fleetiq-train-roadface` |
| `scripts/roadface/evaluate_roadface_outputs.py` | `uv run --package fleetiq-training-roadface fleetiq-evaluate-roadface` |
| `scripts/roadface/relabel_locateanything.py` | `uv run --package fleetiq-training-roadface --extra models fleetiq-label-roadface` |
| `scripts/render_trip_dashboard.py` | `tools/visualization/trip_player.py` |
| `scripts/generate_dataset_notebooks.py` | `tools/dataset/generate_notebooks.py` |
| `scripts/pptx/` | `tools/presentation/` |
| Root proposal deck/PDF | `docs/proposal/` |
| Root papers/clones/weights | `research/papers/raw/`, `research/third-party/`, `artifacts/models/checkpoints/` |

Legacy wrappers are intentionally not preserved.

## Deployment

- [Local Compose](infra/compose/README.md)
- [AWS ECS EC2, SageMaker, and IoT](docs/runbooks/aws-deploy.md)
- [CarSky Android Automotive HMI](docs/runbooks/carsky-deploy.md)

AWS infrastructure is synthesis-tested but not deployed by repository tests.
The current API uses in-memory stores for the hackathon bootstrap; production
persistence is blocked until the PostgreSQL adapter and migrations are complete.

## Team Ownership

| Member | GitHub | Primary boundary |
| --- | --- | --- |
| Phi | `hminhphi` | Road-facing camera, automotive integration, perception delivery |
| Trung | `hoangtrung1801` | In-cabin DMS and driver-state CV |
| Dũng | `VKUNeMo` | AI agent/NLP and coaching intelligence |
| Kha | `khaphan11` | CV/AI-ML training, depth, detection, lane evaluation |
| Tư | `four2k3` | AI agent, backend/software integration, dashboard support |

Shared payload changes require review of `packages/contracts`. Workstream
outputs cross boundaries through contracts, not imports from another service's
internal package.

## Quality Gates

```powershell
uv lock --check
uv run python -m pytest -v
pnpm --filter @fleetiq/web lint
pnpm --filter @fleetiq/web typecheck
pnpm --filter @fleetiq/web test
pnpm --filter @fleetiq/web build
docker compose --profile full config
```

## Artifacts And Secrets

Commit source, tests, lightweight configs, authored docs, and approved proposal
artifacts. Never commit datasets, model weights, training runs, predictions,
renders, extracted papers, third-party clones, `.env`, AWS credentials, CarSky
API keys, certificates, or private keys.

Use `data/`, `artifacts/`, `research/papers/raw/`, and
`research/third-party/` for local-only content. Store runtime secrets in AWS
Secrets Manager, CI secret storage, or organizer-provided CarSky secret fields.

LocateAnything-3B uses NVIDIA research/non-commercial terms; verify every model
and dataset license before commercial use.
