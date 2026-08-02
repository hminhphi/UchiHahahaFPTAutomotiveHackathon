# FleetIQ Guardian Monorepo Refactor Design

**Status:** Approved for implementation
**Date:** 2026-07-28
**Decision owners:** Team UchiHahaha
**Refactor mode:** Breaking refactor; legacy `scripts/roadface` imports and commands are not preserved

## 1. Objective

Refactor the current research-oriented repository into a deployable monorepo
that five team members can extend in parallel during the hackathon.

The target system must provide:

- A Next.js fleet dashboard.
- A FastAPI control plane with REST and WebSocket interfaces.
- Independent road-facing, DMS, fusion, coaching, and event workers.
- Typed model clients for SageMaker-hosted inference.
- A CarSky Android Automotive coaching integration.
- Reproducible local infrastructure through Docker Compose.
- A production path where frontend and backend run on ECS with the EC2 launch
  type and model inference runs on SageMaker.
- Separate source, training, dataset, generated-artifact, research, and
  proposal areas.
- A README in every major ownership or deployment boundary.

This design supersedes the repository-structure decision in
`2026-07-28-btc-milestone-project-design.md` that retained experiments under
`scripts/roadface`. Product scope, milestones, KPIs, and team ownership in the
earlier design remain valid.

## 2. Architecture Decision

Use a **hybrid service monorepo**.

Runtime components are separated when they have different deployment,
scaling, failure, or ownership characteristics. Shared contracts and pure
domain logic remain installable workspace packages. This avoids both a single
backend process containing every concern and a large number of thin network
microservices.

### 2.1 Runtime Topology

```text
Browser dashboard
  -> ALB HTTPS/WSS
  -> Next.js web + FastAPI API on ECS EC2

Vehicle/replay producers
  -> MQTT telemetry/events
  -> WebSocket camera streams
  -> event gateway and API on ECS EC2

Road-facing/DMS workers
  -> HTTPS InvokeEndpoint
  -> SageMaker detector/depth/lane/DMS endpoints

Road-facing + DMS + vehicle telemetry
  -> fusion worker
  -> risk event + trip score
  -> coaching worker
  -> CarSky REST adapter
  -> CarSky Container Node
  -> KUKSA/VSS or REST bridge
  -> Android Automotive Skycraft/VHAL
```

### 2.2 Production Responsibilities

| Component | Production runtime | Responsibility |
| --- | --- | --- |
| `web` | ECS EC2 | Fleet UI, trip drill-down, live stream, evidence and reports |
| `api` | ECS EC2 | REST control plane, WebSocket sessions, authentication boundary |
| `event-gateway` | ECS EC2 | MQTT validation, normalization, topic routing and dead-letter handling |
| `roadface-worker` | ECS EC2 | Road pipeline orchestration, pre/post-processing, tracking, TTC |
| `dms-worker` | ECS EC2 | Driver-frame orchestration, temporal smoothing and driver-state events |
| `fusion-worker` | ECS EC2 | Time alignment, compound risk, scoring and safety gate |
| `coaching-worker` | ECS EC2 | Coaching policy, delivery, retries and acknowledgements |
| Model endpoints | SageMaker | GPU inference for detector, depth, lane and DMS models |
| Object storage | S3 | Frames, clips, reports, manifests and generated artifacts |
| Event broker | AWS IoT Core | MQTT event and command transport |
| Metadata database | Managed PostgreSQL | Trips, events, scores, jobs and evidence metadata |
| Queue/cache | Managed Redis | Job queue, cache and live-state fan-out |

Local Docker Compose substitutes Mosquitto, PostgreSQL, Redis and mock
SageMaker/CarSky adapters for managed services.

## 3. Target Repository Structure

```text
apps/
  README.md
  web/
    README.md
    Dockerfile
    package.json
    src/
  api/
    README.md
    Dockerfile
    pyproject.toml
    src/fleetiq_api/
    tests/
  carsky-hmi/
    README.md
    Dockerfile
    app/
    carsky/

services/
  README.md
  event-gateway/
  roadface-worker/
  dms-worker/
  fusion-worker/
  coaching-worker/

packages/
  README.md
  contracts/
  data-kit/
  model-clients/
  observability/

ml/
  README.md
  training/
    roadface/
    dms/
  sagemaker/
    detector/
    depth/
    lane/
    dms/
  notebooks/
  configs/

infra/
  README.md
  compose/
  aws/
  docker/

tools/
  README.md
  dataset/
  visualization/
  presentation/

docs/
  README.md
  architecture/
  protocols/
  proposal/
  reference/
  reports/
  runbooks/

research/
  README.md
  papers/
  third-party/

data/
  README.md

artifacts/
  README.md
  models/
  training/
  predictions/
  renders/
  reports/
  presentations/
  research-extracts/
```

Every directory shown directly under `apps`, `services`, `packages`, `ml`,
`infra`, `tools`, `docs`, `research`, `data`, and `artifacts` must explain:

1. Its owner and purpose.
2. What belongs and does not belong there.
3. How to run or validate it.
4. Its inputs, outputs, and dependencies.
5. Whether its contents are committed or generated.

## 4. Code Boundaries

### 4.1 Applications

`apps/web` is a Next.js App Router application built as a standalone Node.js
container. The production ALB is the public reverse proxy. Browser code does
not call SageMaker, MQTT, PostgreSQL, or CarSky directly.

`apps/api` is a FastAPI application. It owns `/api/v1`, WebSocket session
authorization, job submission, query APIs and health endpoints. It delegates
long-running work to workers.

`apps/carsky-hmi` contains the Android Automotive display application and
CarSky deployment material. The Dockerfile builds the artifact; the APK runs
inside the CarSky Skycraft Android guest, not as an ECS service.

### 4.2 Services

Each service directory is independently testable and deployable. It contains
one `pyproject.toml`, one Dockerfile, one source package, tests, health checks
and a README.

- `event-gateway` owns MQTT ingress/egress and schema validation.
- `roadface-worker` owns frame orchestration, road-object association, depth,
  lane filtering, relative speed and TTC post-processing.
- `dms-worker` owns driver-frame orchestration and temporal state generation.
- `fusion-worker` owns alignment, compound risk and explainable scoring.
- `coaching-worker` owns coaching policy and CarSky delivery.

Workers call model endpoints through `packages/model-clients`; they do not
embed model-specific boto3 calls throughout domain code.

### 4.3 Shared Packages

- `contracts` provides versioned Pydantic models and generated JSON Schema.
- `data-kit` provides Practice Dataset discovery, KITTI calibration, stereo,
  depth, labels, driver frames and telemetry loading.
- `model-clients` provides typed SageMaker and local mock adapters.
- `observability` provides structured logging, correlation IDs, metrics and
  secret-redaction helpers.

Shared packages must not import applications or services.

### 4.4 ML and Training

Training code never becomes an application dependency.

- `ml/training/roadface` receives relabeling, lane, object detection, depth,
  benchmark and evaluation programs.
- `ml/training/dms` receives driver-state preparation, training and evaluation.
- `ml/sagemaker/<model>` contains endpoint inference handlers, model packaging
  and endpoint-specific requirements.
- `ml/notebooks` contains experiments and analysis only.
- `ml/configs` stores committed, reproducible configurations without weights,
  credentials or local absolute paths.

## 5. Protocol Design

### 5.1 HTTP

All normal request/response features use HTTPS under `/api/v1`:

- Trip, vehicle and driver queries.
- Event, score, trajectory and report queries.
- Analysis job creation and status.
- Presigned S3 evidence URLs.
- Coaching history and manual acknowledgement.

Every envelope contains `schema_version`, `request_id` and an RFC 3339 UTC
timestamp. Mutating requests accept an `Idempotency-Key` header.

### 5.2 WebSocket

- `/ws/v1/trips/{trip_id}/camera/{view}` streams JPEG binary frames with a
  compact metadata header containing frame index, timestamp, dimensions and
  correlation ID.
- `/ws/v1/trips/{trip_id}/live` streams JSON telemetry, TTC, DMS and risk state.

Camera frames are not base64 encoded. Slow clients may lose camera frames but
must receive the latest live state. Risk events are persisted and queried over
HTTP even if a WebSocket client disconnects.

### 5.3 MQTT

MQTT carries small events and commands, never images or video:

```text
fleetiq/v1/vehicles/{vehicle_id}/telemetry
fleetiq/v1/trips/{trip_id}/risk
fleetiq/v1/vehicles/{vehicle_id}/coaching/command
fleetiq/v1/vehicles/{vehicle_id}/coaching/ack
fleetiq/v1/services/{service}/status
fleetiq/v1/dead-letter/{source}
```

Telemetry uses QoS 0. Risk, coaching command and coaching acknowledgement use
QoS 1. Only service status may be retained.

### 5.4 SageMaker

Realtime endpoints accept small JPEG/tensor payloads and return a versioned
model-output contract. Batch or replay analysis passes an S3 manifest instead
of proxying a full video through the API.

Endpoint selection is configuration-driven:

```text
SAGEMAKER_DETECTOR_ENDPOINT
SAGEMAKER_DEPTH_ENDPOINT
SAGEMAKER_LANE_ENDPOINT
SAGEMAKER_DMS_ENDPOINT
```

Local and automated tests use an adapter with the same interface and
deterministic fixture outputs.

### 5.5 CarSky

The approved CarSky model remains:

```text
Blueprint -> Deploy -> Room -> Device -> Widget
```

FleetIQ does not require the Android guest to connect directly to the MQTT
broker. `coaching-worker` consumes a FleetIQ coaching event and calls the
CarSky adapter over HTTPS. A Container Node in the CarSky Room bridges the
coaching signal to KUKSA/VSS or the documented REST path. The Android
Automotive Skycraft guest reads the corresponding vehicle property through
VHAL and renders the coaching UI. A Screen widget provides live evidence.

## 6. Reliability and Security

All cross-service records contain:

- `event_id`
- `correlation_id`
- `trip_id`
- `frame_index` when frame-derived
- `schema_version`
- `producer`
- `occurred_at`
- `idempotency_key` for commands and mutations

SageMaker and CarSky clients use bounded timeouts, exponential backoff and
explicit retry limits. Exhausted calls create a dead-letter record and a
visible degraded-state event. Model failure does not terminate the API.

Secrets are provided through environment variables locally and AWS-managed
secret injection in production. Logs must redact API keys, authorization
headers and presigned URL query strings.

## 7. Docker and Deployment

### 7.1 Local

The root `compose.yaml` includes:

- `web`
- `api`
- `event-gateway`
- `roadface-worker`
- `dms-worker`
- `fusion-worker`
- `coaching-worker`
- `postgres`
- `redis`
- `mosquitto`
- deterministic local model and CarSky mocks

Compose profiles keep the minimum developer startup small:

- `core`: web, API and data services.
- `perception`: road-facing and DMS workers.
- `full`: fusion, coaching and all mocks.

Each framework receives a multi-stage Dockerfile:

- Next.js standalone Node.js runtime for `web`.
- uv-based Python 3.12 images for API and workers.
- Gradle/Android build image for `carsky-hmi`.
- Model-serving images under `ml/sagemaker`, not in ECS Compose.

### 7.2 AWS

Infrastructure code under `infra/aws` defines:

- VPC and security boundaries.
- ECS cluster with EC2 capacity.
- ALB routes for Next.js, FastAPI and WSS.
- ECS task definitions and services.
- S3 artifact buckets.
- SageMaker endpoint references and IAM invocation permissions.
- AWS IoT Core policies/topics.
- PostgreSQL and Redis connection configuration.
- CloudWatch log groups and health alarms.

This refactor provides deployment-ready configuration and documentation. It
does not create billable AWS resources without a separate explicit action.

## 8. File Migration

| Current location | Target location |
| --- | --- |
| `scripts/roadface` runtime pipeline | `services/roadface-worker` |
| `scripts/roadface` training/evaluation | `ml/training/roadface` |
| `scripts/roadface` visualization/audit tools | `tools/visualization/roadface` |
| `scripts/render_trip_dashboard.py` | `tools/visualization/trip_player.py` |
| `scripts/generate_dataset_notebooks.py` | `tools/dataset/generate_notebooks.py` |
| `scripts/pptx` | `tools/presentation` |
| `notebooks` | `ml/notebooks` |
| Reusable loader/calibration code | `packages/data-kit` |
| Shared event/model types | `packages/contracts` |
| Root proposal PPTX/PDF | `docs/proposal` |
| Organizer reference files | `docs/reference/organizer` |
| CarSky and Digital Cockpit HTML | `docs/reference/carsky` |
| Architecture diagrams | `docs/architecture/diagrams` |
| Progress report and one-pager | `docs/reports/progress` |
| Raw papers | `research/papers/raw` |
| Cloned repositories | `research/third-party` |
| Root model weights | `artifacts/models/checkpoints` |
| Training runs | `artifacts/training` |
| Prediction CSV/JSON/video | `artifacts/predictions` |
| PPTX generated assets | `artifacts/presentations` |
| Extracted paper pages | `artifacts/research-extracts` |

Large local moves must preserve ignored status. Dataset content remains under
`data` and is never renamed internally because existing organizer paths are
part of the input contract.

## 9. Developer Workflow

Python projects use a uv workspace with one lockfile and Python 3.12. Each
workspace member declares only its own direct dependencies. The frontend uses
a pnpm workspace and its own lockfile. Root task commands provide a consistent
entry point for setup, lint, test, build and Compose.

Primary commands after the refactor:

```powershell
uv sync --all-packages
uv run pytest
pnpm install
pnpm --filter @fleetiq/web test
docker compose --profile core up --build
docker compose --profile full up --build
```

Old commands and imports under `scripts/roadface` are intentionally removed.
The root README includes a migration table for common commands.

## 10. Testing Strategy

Required automated checks:

- Unit tests for contracts, loaders, engines and model clients.
- Contract tests that serialize and validate every HTTP, MQTT, worker and
  SageMaker payload.
- FastAPI API and WebSocket tests.
- MQTT publish/subscribe and QoS integration tests.
- Deterministic local model-adapter tests.
- Docker image build checks and service health checks.
- Compose smoke test covering API health, MQTT event flow, one camera frame,
  worker mock inference, fusion output and coaching acknowledgement.
- Next.js lint, typecheck, component tests and production build.

Live SageMaker, AWS IoT Core and CarSky smoke tests are opt-in and must skip
cleanly when credentials are absent.

## 11. Acceptance Criteria

The refactor is complete when:

1. The repository matches the target ownership and deployment boundaries.
2. Every major folder and deployable contains an actionable README.
3. No tracked code imports from or documents commands under `scripts/roadface`.
4. Existing road-facing unit tests pass from their new package locations.
5. Root Python and frontend dependency locks are reproducible.
6. Every deployable image builds or has a documented external build
   prerequisite for the Android SDK.
7. Docker Compose validates and its core smoke checks pass.
8. Protocol schemas and topic names are documented and tested.
9. AWS deployment files target ECS EC2 plus SageMaker without embedding
   credentials or creating resources automatically.
10. CarSky files document Blueprint, Container Node, bridge, Skycraft/VHAL and
    Screen widget responsibilities.
11. Data, weights, generated outputs, raw research corpora and secrets remain
    ignored by Git after moving.
12. The root README gives new contributors one setup path, architecture links,
    ownership boundaries and replacement commands for the breaking refactor.

## 12. Non-Goals

- Running GPU model inference inside ECS application containers.
- Deploying Kubernetes, Kafka or a service mesh.
- Making each Python class a network service.
- Streaming camera bytes through MQTT.
- Committing datasets, weights, generated videos or credentials.
- Provisioning billable AWS or CarSky resources during the repository refactor.

## 13. Reference Guidance

 
The design follows the official guidance for:

- uv workspaces with a shared lockfile and per-member `pyproject.toml`.
- Next.js App Router self-hosting behind a reverse proxy.
- FastAPI container deployment.
- AWS ECS EC2, SageMaker endpoint invocation and AWS IoT Core MQTT.
- The organizer-provided `docs/Car-Sky-Platform.html` platform model.
