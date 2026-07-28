# FleetIQ Guardian Monorepo Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the research-oriented repository layout with a tested hybrid-service monorepo for Next.js, FastAPI, model workers, SageMaker inference, MQTT/WebSocket event flow, ECS EC2 deployment, and CarSky Android Automotive coaching.

**Architecture:** Deployable applications and workers live in `apps/` and `services/`; stable Python interfaces live in uv workspace packages under `packages/`; GPU training and SageMaker serving live under `ml/`. Local development uses Docker Compose with deterministic model and CarSky mocks, while production configuration targets ECS EC2, SageMaker, AWS IoT Core, S3, PostgreSQL, and Redis.

**Tech Stack:** Python 3.12, uv workspaces, Pydantic 2, FastAPI, boto3, paho-mqtt, Redis, PostgreSQL, Next.js App Router, TypeScript, pnpm, Android Automotive/Kotlin, Docker Compose, Mosquitto, AWS CDK for Python, ECS EC2, SageMaker, AWS IoT Core, S3.

## Global Constraints

- This is a breaking refactor; do not keep legacy `scripts/roadface` wrappers or imports.
- Preserve the organizer dataset layout under `data/Practice_Dataset` and `data/Hackathon_Dataset_Redacted`.
- Keep Python at `>=3.12,<3.13`.
- Frontend and backend production containers target ECS with the EC2 launch type.
- GPU inference runs on SageMaker endpoints, not inside ECS application containers.
- MQTT carries events and commands only; camera bytes use WebSocket and evidence media uses S3.
- The CarSky path is FleetIQ HTTPS adapter -> Container Node -> KUKSA/VSS or REST bridge -> Android Automotive Skycraft/VHAL.
- CPU tests cannot require AWS credentials, a GPU, the Android SDK, or a live CarSky Room.
- Data, weights, generated media, raw papers, cloned repositories, secrets, and `.superpowers/` remain outside Git.
- Do not modify or discard unrelated user files while moving repository content.

---

## Locked File Map

### Python workspace members

```text
apps/api
services/event-gateway
services/roadface-worker
services/dms-worker
services/fusion-worker
services/coaching-worker
packages/contracts
packages/data-kit
packages/model-clients
packages/observability
infra/aws
```

### Road-facing source split

```text
services/roadface-worker/src/fleetiq_roadface/
  cli.py                 Run the road-facing inference pipeline
  depth.py               GT, stereo and ROI distance
  geometry.py            Projection and camera geometry
  lane.py                Plane-based road/lane corridor logic
  birdseye.py            Curved-lane bird-eye tracker
  pipeline.py            Frame orchestration
  rendering.py           Evidence overlay
  tracking.py            Association, relative speed and TTC
  types.py               Road-facing internal dataclasses

ml/training/roadface/src/fleetiq_training_roadface/
  label_locateanything.py
  prepare_dataset.py
  train_models.py
  evaluate.py
  lane_auto_label.py
  yolop_labels.py

tools/visualization/roadface/
  annotate_lane_mask.py
  audit_lane_models.py
  audit_plane_lane.py
  debug_lane_evidence.py
  demo_lane_mmae_offset.py
  demo_plane_lane_offset.py
  visualize_kitti_labels.py
  visualize_outputs.py
  visualize_yolop_lane_offset.py
```

### Generated and local-only targets

```text
artifacts/models/checkpoints
artifacts/models/cache
artifacts/training/roadface
artifacts/predictions/roadface
artifacts/renders
artifacts/reports
artifacts/presentations
artifacts/research-extracts
research/papers/raw
research/third-party
```

---

### Task 1: Root Workspace, Guardrails, and Ownership Skeleton

**Files:**
- Create: `tests/architecture/test_repository_skeleton.py`
- Create: `apps/README.md`
- Create: `services/README.md`
- Create: `packages/README.md`
- Create: `ml/README.md`
- Create: `infra/README.md`
- Create: `tools/README.md`
- Create: `research/README.md`
- Create: `data/README.md`
- Create: `artifacts/README.md`
- Create: `pnpm-workspace.yaml`
- Modify: `.gitignore`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: Approved directory layout from the design spec.
- Produces: uv workspace discovery, pnpm workspace discovery, ignored local-output policy, and ownership rules used by every later task.

- [ ] **Step 1: Write the failing repository skeleton test**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ("apps", "services", "packages", "ml", "infra", "tools", "research", "data", "artifacts")


def test_major_boundaries_have_readmes() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name / "README.md").is_file()]
    assert missing == []


def test_local_companion_and_generated_roots_are_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in (".superpowers/", "data/", "artifacts/", "research/papers/raw/", "research/third-party/"):
        assert entry in ignore
```

- [ ] **Step 2: Run the skeleton test and verify it fails**

Run: `uv run pytest tests/architecture/test_repository_skeleton.py -v`

Expected: FAIL because the new boundary READMEs and `.superpowers/` ignore rule do not exist.

- [ ] **Step 3: Create the ownership skeleton and workspace configuration**

Set the root uv workspace members to:

```toml
[tool.uv.workspace]
members = [
    "apps/*",
    "services/*",
    "packages/*",
    "ml/training/*",
    "infra/*",
]
exclude = [
    "apps/web",
    "apps/carsky-hmi",
    "infra/compose",
    "infra/docker",
]
```

Set `pnpm-workspace.yaml` to:

```yaml
packages:
  - apps/web
```

Add a root development dependency group containing `pytest`, `pytest-cov`,
`ruff`, and `mypy` so architecture tests run before application members exist.
Replace broad `data/` and `artifacts/` rules with:

```gitignore
data/*
!data/README.md
artifacts/*
!artifacts/README.md
```

This keeps the boundary READMEs tracked while all local content below them
remains ignored.
Each boundary README must state purpose, owner, committed/generated policy, inputs, outputs, and its validation command.

- [ ] **Step 4: Run the skeleton test**

Run: `uv run pytest tests/architecture/test_repository_skeleton.py -v`

Expected: PASS.

- [ ] **Step 5: Verify ignored local roots remain ignored**

Run: `git check-ignore data/Practice_Dataset artifacts/roadface .superpowers`

Expected: all three local paths are printed.

- [ ] **Step 6: Commit**

```powershell
git add .gitignore pyproject.toml pnpm-workspace.yaml apps/README.md services/README.md packages/README.md ml/README.md infra/README.md tools/README.md research/README.md data/README.md artifacts/README.md tests/architecture/test_repository_skeleton.py
git commit -m "chore: establish FleetIQ monorepo boundaries"
```

### Task 2: Canonical Contracts and Topic Registry

**Files:**
- Create: `packages/contracts/README.md`
- Create: `packages/contracts/pyproject.toml`
- Create: `packages/contracts/src/fleetiq_contracts/__init__.py`
- Create: `packages/contracts/src/fleetiq_contracts/base.py`
- Create: `packages/contracts/src/fleetiq_contracts/events.py`
- Create: `packages/contracts/src/fleetiq_contracts/inference.py`
- Create: `packages/contracts/src/fleetiq_contracts/topics.py`
- Create: `packages/contracts/scripts/export_schema.py`
- Create: `packages/contracts/tests/test_events.py`
- Create: `packages/contracts/tests/test_topics.py`
- Create: `docs/protocols/README.md`
- Create: `docs/protocols/events-v1.md`

**Interfaces:**
- Consumes: Python 3.12 and Pydantic 2.
- Produces: `EventEnvelope`, `TelemetryEvent`, `RiskEvent`, `CoachingCommand`, `CoachingAck`, `InferenceRequest`, `InferenceResponse`, and `TopicRegistry`.

- [ ] **Step 1: Write failing contract tests**

```python
from datetime import UTC, datetime
from uuid import uuid4

from fleetiq_contracts.events import RiskEvent
from fleetiq_contracts.topics import TopicRegistry


def test_risk_event_round_trip_keeps_trace_fields() -> None:
    event_id = uuid4()
    event = RiskEvent(
        schema_version="1.0",
        event_id=event_id,
        correlation_id="trip-01:frame-100",
        trip_id="T01-Sample",
        frame_index=100,
        producer="fusion-worker",
        occurred_at=datetime(2026, 7, 28, tzinfo=UTC),
        event_type="short_ttc",
        severity=4,
        confidence=0.91,
        explanation="TTC below 1.5 seconds",
    )
    restored = RiskEvent.model_validate_json(event.model_dump_json())
    assert restored.event_id == event_id
    assert restored.frame_index == 100


def test_topic_registry_builds_versioned_topics() -> None:
    assert TopicRegistry.risk("trip-a") == "fleetiq/v1/trips/trip-a/risk"
    assert TopicRegistry.coaching_ack("vehicle-a") == (
        "fleetiq/v1/vehicles/vehicle-a/coaching/ack"
    )
```

- [ ] **Step 2: Run tests and verify import failure**

Run: `uv run --package fleetiq-contracts pytest packages/contracts/tests -v`

Expected: FAIL because `fleetiq_contracts` does not exist.

- [ ] **Step 3: Implement strict versioned models**

Use `ConfigDict(extra="forbid")`. Constrain severity to `1..5`, confidence to
`0..1`, require timezone-aware timestamps, and reject `/`, `+`, and `#` in MQTT
identifier segments. Model inference outputs as typed detections, lane state,
depth state, and driver state rather than unstructured dictionaries.

- [ ] **Step 4: Generate and commit JSON Schema**

Create `docs/protocols/schemas/events-v1.json` from the Pydantic models with a
small script at `packages/contracts/scripts/export_schema.py`.

Run: `uv run --package fleetiq-contracts python packages/contracts/scripts/export_schema.py`

Expected: the generated schema validates the sample payloads documented in
`docs/protocols/events-v1.md`.

- [ ] **Step 5: Run contract tests**

Run: `uv run --package fleetiq-contracts pytest packages/contracts/tests -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add packages/contracts docs/protocols
git commit -m "feat: define versioned FleetIQ contracts"
```

### Task 3: Dataset and Calibration Package

**Files:**
- Create: `packages/data-kit/README.md`
- Create: `packages/data-kit/pyproject.toml`
- Create: `packages/data-kit/src/fleetiq_data/__init__.py`
- Create: `packages/data-kit/src/fleetiq_data/paths.py`
- Create: `packages/data-kit/src/fleetiq_data/calibration.py`
- Create: `packages/data-kit/src/fleetiq_data/kitti.py`
- Create: `packages/data-kit/src/fleetiq_data/trips.py`
- Create: `packages/data-kit/src/fleetiq_data/telemetry.py`
- Create: `packages/data-kit/tests/test_calibration.py`
- Create: `packages/data-kit/tests/test_kitti.py`
- Create: `packages/data-kit/tests/test_trips.py`

**Interfaces:**
- Consumes: `FLEETIQ_DATA_ROOT` or an explicit `Path`.
- Produces: `DatasetPaths`, `TripRecord`, `KittiObject`, `Calibration`, `discover_trips`, `resolve_trip`, `load_trip_document`, `parse_calibration`, `parse_kitti_labels`, and `find_frame`.

- [ ] **Step 1: Write synthetic loader tests**

```python
import gzip
import json
from pathlib import Path

from fleetiq_data.calibration import parse_calibration
from fleetiq_data.trips import discover_trips


def test_parse_stereo_projection_and_baseline(tmp_path: Path) -> None:
    calib = tmp_path / "000000.txt"
    calib.write_text(
        "P2: 700 0 320 0 0 700 180 0 0 0 1 0\n"
        "P3: 700 0 320 -210 0 700 180 0 0 0 1 0\n",
        encoding="utf-8",
    )
    parsed = parse_calibration(calib)
    assert parsed.baseline_m == 0.3
    assert parsed.fx == 700.0


def test_discover_trips_uses_explicit_root(tmp_path: Path) -> None:
    trip = tmp_path / "T01-Sample"
    trip.mkdir()
    with gzip.open(trip / "T01-Sample.json.gz", "wt", encoding="utf-8") as handle:
        json.dump({"frames": []}, handle)
    assert [item.trip_id for item in discover_trips(tmp_path)] == ["T01-Sample"]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --package fleetiq-data-kit pytest packages/data-kit/tests -v`

Expected: FAIL because the package does not exist.

- [ ] **Step 3: Extract loader code without global project paths**

Move dataset discovery, gzip loading, calibration parsing, KITTI parsing, image
lookup, sparse depth lookup, and telemetry normalization out of
`scripts/roadface/roadface_lib.py` and `scripts/render_trip_dashboard.py`.
All functions must accept explicit roots; only `DatasetPaths.from_env()` reads
`FLEETIQ_DATA_ROOT`.

- [ ] **Step 4: Run package tests**

Run: `uv run --package fleetiq-data-kit pytest packages/data-kit/tests -v`

Expected: PASS.

- [ ] **Step 5: Smoke test the local Practice Dataset**

Run: `uv run --package fleetiq-data-kit python -m fleetiq_data.trips --root data/Practice_Dataset/Practice_Dataset`

Expected: six Practice Dataset trip identifiers are printed when the local
dataset is present; otherwise the command exits with a clear missing-root
message and status 2.

- [ ] **Step 6: Commit**

```powershell
git add packages/data-kit
git commit -m "refactor: extract reusable dataset package"
```

### Task 4: Road-Facing Runtime Engine

**Files:**
- Create: `services/roadface-worker/README.md`
- Create: `services/roadface-worker/pyproject.toml`
- Create: `services/roadface-worker/Dockerfile`
- Create: `services/roadface-worker/src/fleetiq_roadface/__init__.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/types.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/geometry.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/depth.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/lane.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/birdseye.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/tracking.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/rendering.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/pipeline.py`
- Create: `services/roadface-worker/src/fleetiq_roadface/cli.py`
- Move: `tests/test_carnd_lane_tracker.py` -> `services/roadface-worker/tests/test_birdseye.py`
- Create: `services/roadface-worker/tests/test_depth.py`
- Create: `services/roadface-worker/tests/test_tracking.py`
- Create: `services/roadface-worker/tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: `fleetiq_data` records and `fleetiq_contracts.InferenceResponse`.
- Produces: `RoadFrameResult`, `Detection`, `LaneEstimate`, `TrackedObstacle`, and the `fleetiq-roadface` CLI.

- [ ] **Step 1: Move the existing lane test and update its import**

Change:

```python
from scripts.roadface.carnd_lane_tracker import _perspective_matrices, detect_birdseye_lane
```

to:

```python
from fleetiq_roadface.birdseye import _perspective_matrices, detect_birdseye_lane
```

- [ ] **Step 2: Run the moved test and verify failure**

Run: `uv run --package fleetiq-roadface pytest services/roadface-worker/tests/test_birdseye.py -v`

Expected: FAIL because `fleetiq_roadface.birdseye` has not been created.

- [ ] **Step 3: Split roadface runtime by responsibility**

Move code from `roadface_lib.py`, `carnd_lane_tracker.py`, and
`run_roadface_pipeline.py` according to the locked source split. Remove
`PROJECT_ROOT`, `PRACTICE_ROOT`, and `REDACTED_ROOT` from the service. Inject
dataset paths and model clients into `RoadfacePipeline`.

- [ ] **Step 4: Add tracking and distance tests**

```python
from fleetiq_roadface.tracking import ClosingSpeedEstimator


def test_closing_speed_and_ttc_use_frame_delta() -> None:
    estimator = ClosingSpeedEstimator(smoothing_alpha=1.0)
    estimator.update(track_id=7, timestamp_s=0.0, distance_m=20.0)
    state = estimator.update(track_id=7, timestamp_s=0.5, distance_m=18.0)
    assert state.relative_speed_mps == 4.0
    assert state.ttc_s == 4.5
```

Add stereo tests using synthetic shifted grayscale images and explicit
calibration. Add a contract test asserting that one frame result serializes to
`InferenceResponse` without extra keys.

- [ ] **Step 5: Run road-facing tests**

Run: `uv run --package fleetiq-roadface pytest services/roadface-worker/tests -v`

Expected: PASS.

- [ ] **Step 6: Run one local frame through the new CLI**

Run: `uv run --package fleetiq-roadface fleetiq-roadface --dataset practice --trip T01-Sample --start 0 --end 0 --depth-source gt`

Expected: one frame result is written under
`artifacts/predictions/roadface/T01-Sample/` when the local dataset is present.

- [ ] **Step 7: Commit**

```powershell
git add services/roadface-worker tests/test_carnd_lane_tracker.py
git commit -m "refactor: package road-facing runtime engine"
```

### Task 5: Road-Facing Training, Relabeling, and Visualization

**Files:**
- Create: `ml/training/README.md`
- Create: `ml/training/roadface/README.md`
- Create: `ml/training/roadface/pyproject.toml`
- Create: `ml/training/roadface/src/fleetiq_training_roadface/`
- Move: `tests/test_locateanything_labels.py` -> `ml/training/roadface/tests/test_locateanything_labels.py`
- Create: `tools/visualization/README.md`
- Create: `tools/visualization/roadface/README.md`
- Create: `tools/dataset/README.md`
- Create: `tools/presentation/README.md`
- Move: road-facing annotation, audit, demo, and visualization scripts according to the locked file map
- Move: `scripts/render_trip_dashboard.py` -> `tools/visualization/trip_player.py`
- Move: `scripts/generate_dataset_notebooks.py` -> `tools/dataset/generate_notebooks.py`
- Move: `scripts/pptx/` -> `tools/presentation/`
- Move: `notebooks/` -> `ml/notebooks/`

**Interfaces:**
- Consumes: `fleetiq_data` and `fleetiq_roadface`.
- Produces: training/relabeling entry points and user-facing visualization tools without importing `scripts`.

- [ ] **Step 1: Move the LocateAnything test and update imports**

```python
from fleetiq_training_roadface.label_locateanything import (
    LocatedBox,
    deduplicate_boxes,
    kitti_2d_line,
    parse_locateanything_answer,
)
```

- [ ] **Step 2: Run the moved test and verify failure**

Run: `uv run --package fleetiq-training-roadface pytest ml/training/roadface/tests -v`

Expected: FAIL because the training package has not been created.

- [ ] **Step 3: Move all training and tool programs**

Define console entry points:

```toml
[project.scripts]
fleetiq-label-roadface = "fleetiq_training_roadface.label_locateanything:main"
fleetiq-prepare-roadface = "fleetiq_training_roadface.prepare_dataset:main"
fleetiq-train-roadface = "fleetiq_training_roadface.train_models:main"
fleetiq-evaluate-roadface = "fleetiq_training_roadface.evaluate:main"
```

Update every moved script to import installed packages rather than modifying
`sys.path` or importing from `scripts`.

- [ ] **Step 4: Run training parser tests and CLI help**

Run: `uv run --package fleetiq-training-roadface pytest ml/training/roadface/tests -v`

Run: `uv run --package fleetiq-training-roadface fleetiq-label-roadface --help`

Expected: tests pass and CLI help exits 0 without loading model weights.

- [ ] **Step 5: Run import audit**

Run: `rg -n "scripts[./\\\\]roadface|from scripts|import scripts" ml tools services packages tests`

Expected: no matches.

- [ ] **Step 6: Commit**

```powershell
git add ml tools services/roadface-worker tests scripts notebooks
git commit -m "refactor: separate road-facing training and tools"
```

### Task 6: SageMaker Model Client Package

**Files:**
- Create: `packages/model-clients/README.md`
- Create: `packages/model-clients/pyproject.toml`
- Create: `packages/model-clients/src/fleetiq_model_clients/__init__.py`
- Create: `packages/model-clients/src/fleetiq_model_clients/base.py`
- Create: `packages/model-clients/src/fleetiq_model_clients/config.py`
- Create: `packages/model-clients/src/fleetiq_model_clients/local.py`
- Create: `packages/model-clients/src/fleetiq_model_clients/sagemaker.py`
- Create: `packages/model-clients/tests/fixtures/road_response.json`
- Create: `packages/model-clients/tests/fixtures/dms_response.json`
- Create: `packages/model-clients/tests/test_local.py`
- Create: `packages/model-clients/tests/test_sagemaker.py`

**Interfaces:**
- Consumes: `InferenceRequest`.
- Produces: `ModelClient.infer(request) -> InferenceResponse`,
  `LocalFixtureModelClient`, and `SageMakerModelClient`.

- [ ] **Step 1: Write the failing adapter tests**

```python
from fleetiq_model_clients.local import LocalFixtureModelClient


def test_local_client_returns_deterministic_contract() -> None:
    client = LocalFixtureModelClient.from_fixture("tests/fixtures/road_response.json")
    first = client.infer_bytes(b"same-frame", content_type="image/jpeg")
    second = client.infer_bytes(b"same-frame", content_type="image/jpeg")
    assert first == second
    assert first.schema_version == "1.0"
```

Mock `boto3.client("sagemaker-runtime").invoke_endpoint` and assert endpoint
name, content type, accept type, custom attributes and body are passed exactly.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --package fleetiq-model-clients pytest packages/model-clients/tests -v`

Expected: FAIL because the package does not exist.

- [ ] **Step 3: Implement adapters and endpoint configuration**

Require explicit endpoint names from:

```text
SAGEMAKER_DETECTOR_ENDPOINT
SAGEMAKER_DEPTH_ENDPOINT
SAGEMAKER_LANE_ENDPOINT
SAGEMAKER_DMS_ENDPOINT
```

Use botocore connect/read timeouts, a maximum of three attempts, and no
credential values in exceptions or logs.

- [ ] **Step 4: Run package tests**

Run: `uv run --package fleetiq-model-clients pytest packages/model-clients/tests -v`

Expected: PASS with no network calls.

- [ ] **Step 5: Commit**

```powershell
git add packages/model-clients
git commit -m "feat: add typed SageMaker model clients"
```

### Task 7: Observability and FastAPI Control Plane

**Files:**
- Create: `packages/observability/README.md`
- Create: `packages/observability/pyproject.toml`
- Create: `packages/observability/src/fleetiq_observability/`
- Create: `packages/observability/tests/test_redaction.py`
- Create: `apps/api/README.md`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/Dockerfile`
- Create: `apps/api/src/fleetiq_api/main.py`
- Create: `apps/api/src/fleetiq_api/config.py`
- Create: `apps/api/src/fleetiq_api/dependencies.py`
- Create: `apps/api/src/fleetiq_api/routes/health.py`
- Create: `apps/api/src/fleetiq_api/routes/trips.py`
- Create: `apps/api/src/fleetiq_api/routes/jobs.py`
- Create: `apps/api/src/fleetiq_api/routes/websocket.py`
- Create: `apps/api/src/fleetiq_api/ws/frame_protocol.py`
- Create: `apps/api/tests/test_health.py`
- Create: `apps/api/tests/test_frame_protocol.py`
- Create: `apps/api/tests/test_live_socket.py`

**Interfaces:**
- Consumes: contracts, Redis job submission interface, and evidence repository interface.
- Produces: `create_app()`, `/health/live`, `/health/ready`, `/api/v1/trips`, `/api/v1/jobs`, `/ws/v1/trips/{trip_id}/camera/{view}`, and `/ws/v1/trips/{trip_id}/live`.

- [ ] **Step 1: Write failing API tests**

```python
from fastapi.testclient import TestClient
from fleetiq_api.main import create_app


def test_health_envelope_has_request_id() -> None:
    response = TestClient(create_app(testing=True)).get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["request_id"]
```

Add a frame protocol test for:

```text
4-byte unsigned metadata length | UTF-8 JSON metadata | JPEG bytes
```

Assert malformed lengths and frame sizes above the configured maximum close
the socket with code 1009.

- [ ] **Step 2: Run API tests and verify failure**

Run: `uv run --package fleetiq-api pytest apps/api/tests -v`

Expected: FAIL because the API package does not exist.

- [ ] **Step 3: Implement the minimal control plane**

Use application lifespan for Redis/database clients, dependency injection for
tests, CORS restricted by `FLEETIQ_ALLOWED_ORIGINS`, and structured request
logging with redaction.

- [ ] **Step 4: Run tests and OpenAPI smoke check**

Run: `uv run --package fleetiq-api pytest apps/api/tests -v`

Run:

```powershell
uv run --package fleetiq-api python -c "from fastapi.testclient import TestClient; from fleetiq_api.main import app; d=TestClient(app).get('/openapi.json').json(); assert '/api/v1/trips' in d['paths']; assert '/api/v1/jobs' in d['paths']"
```

Expected: tests pass; `/openapi.json` includes `/api/v1/trips` and
`/api/v1/jobs`.

- [ ] **Step 5: Commit**

```powershell
git add packages/observability apps/api
git commit -m "feat: scaffold FleetIQ FastAPI control plane"
```

### Task 8: MQTT Event Gateway

**Files:**
- Create: `services/event-gateway/README.md`
- Create: `services/event-gateway/pyproject.toml`
- Create: `services/event-gateway/Dockerfile`
- Create: `services/event-gateway/src/fleetiq_event_gateway/__init__.py`
- Create: `services/event-gateway/src/fleetiq_event_gateway/config.py`
- Create: `services/event-gateway/src/fleetiq_event_gateway/handler.py`
- Create: `services/event-gateway/src/fleetiq_event_gateway/main.py`
- Create: `services/event-gateway/src/fleetiq_event_gateway/transport.py`
- Create: `services/event-gateway/tests/test_handler.py`
- Create: `services/event-gateway/tests/test_dead_letter.py`

**Interfaces:**
- Consumes: MQTT topic and payload plus `TopicRegistry`.
- Produces: validated event dispatch, status heartbeat, coaching publish, and dead-letter publish.

- [ ] **Step 1: Write failing gateway tests**

```python
from fleetiq_event_gateway.handler import EventHandler


def test_invalid_risk_payload_goes_to_dead_letter(fake_transport) -> None:
    handler = EventHandler(fake_transport)
    handler.handle("fleetiq/v1/trips/T01-Sample/risk", b'{"severity": 99}')
    assert fake_transport.published[0].topic == "fleetiq/v1/dead-letter/event-gateway"
    assert fake_transport.published[0].qos == 1
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --package fleetiq-event-gateway pytest services/event-gateway/tests -v`

Expected: FAIL because the gateway package does not exist.

- [ ] **Step 3: Implement transport-independent routing**

Keep Paho callbacks in `transport.py`; keep validation and routing in
`handler.py`. Publish telemetry with QoS 0; publish risk, coaching and
dead-letter messages with QoS 1. Retain only status heartbeats.

- [ ] **Step 4: Run tests**

Run: `uv run --package fleetiq-event-gateway pytest services/event-gateway/tests -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add services/event-gateway
git commit -m "feat: add versioned MQTT event gateway"
```

### Task 9: DMS Worker and SageMaker Handler

**Files:**
- Create: `services/dms-worker/README.md`
- Create: `services/dms-worker/pyproject.toml`
- Create: `services/dms-worker/Dockerfile`
- Create: `services/dms-worker/src/fleetiq_dms/config.py`
- Create: `services/dms-worker/src/fleetiq_dms/smoothing.py`
- Create: `services/dms-worker/src/fleetiq_dms/worker.py`
- Create: `services/dms-worker/src/fleetiq_dms/main.py`
- Create: `services/dms-worker/tests/test_smoothing.py`
- Create: `services/dms-worker/tests/test_worker.py`
- Create: `ml/training/dms/README.md`
- Create: `ml/training/dms/pyproject.toml`
- Create: `ml/training/dms/src/fleetiq_training_dms/`
- Create: `ml/sagemaker/dms/README.md`
- Create: `ml/sagemaker/dms/inference.py`
- Create: `ml/sagemaker/dms/tests/test_inference.py`

**Interfaces:**
- Consumes: driver-frame job and DMS model client.
- Produces: temporally smoothed driver-state events using `attentive`, `distracted`, `drowsy`, and `unknown`.

- [ ] **Step 1: Write a failing temporal smoothing test**

```python
from fleetiq_dms.smoothing import StateSmoother


def test_single_drowsy_spike_does_not_flip_state() -> None:
    smoother = StateSmoother(window_size=5, min_votes=3)
    states = ["attentive", "attentive", "drowsy", "attentive", "attentive"]
    assert [smoother.update(state) for state in states][-1] == "attentive"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --package fleetiq-dms-worker pytest services/dms-worker/tests -v`

Expected: FAIL because the worker package does not exist.

- [ ] **Step 3: Implement worker and handler**

The worker reads driver frame references, invokes the configured DMS endpoint,
applies smoothing, and publishes a contract event. The SageMaker handler
implements `model_fn`, `input_fn`, `predict_fn`, and `output_fn` and can be
tested with a deterministic fake model.

- [ ] **Step 4: Run DMS tests**

Run: `uv run --package fleetiq-dms-worker pytest services/dms-worker/tests -v`

Run: `uv run pytest ml/sagemaker/dms/tests -v`

Expected: PASS without GPU or network.

- [ ] **Step 5: Commit**

```powershell
git add services/dms-worker ml/training/dms ml/sagemaker/dms
git commit -m "feat: add DMS worker and SageMaker handler"
```

### Task 10: Fusion, Scoring, and Coaching Workers

**Files:**
- Create: `services/fusion-worker/README.md`
- Create: `services/fusion-worker/pyproject.toml`
- Create: `services/fusion-worker/Dockerfile`
- Create: `services/fusion-worker/src/fleetiq_fusion/alignment.py`
- Create: `services/fusion-worker/src/fleetiq_fusion/scoring.py`
- Create: `services/fusion-worker/src/fleetiq_fusion/worker.py`
- Create: `services/fusion-worker/tests/test_scoring.py`
- Create: `services/fusion-worker/tests/test_compound_risk.py`
- Create: `services/coaching-worker/README.md`
- Create: `services/coaching-worker/pyproject.toml`
- Create: `services/coaching-worker/Dockerfile`
- Create: `services/coaching-worker/src/fleetiq_coaching/policy.py`
- Create: `services/coaching-worker/src/fleetiq_coaching/carsky.py`
- Create: `services/coaching-worker/src/fleetiq_coaching/worker.py`
- Create: `services/coaching-worker/tests/test_policy.py`
- Create: `services/coaching-worker/tests/test_carsky.py`

**Interfaces:**
- Consumes: road, DMS and telemetry events.
- Produces: explainable risk score, compound risk events, safe coaching commands, and delivery acknowledgements.

- [ ] **Step 1: Write failing compound-risk tests**

```python
from fleetiq_fusion.scoring import RiskScorer


def test_distraction_plus_short_ttc_increases_severity_once() -> None:
    result = RiskScorer().score(
        ttc_s=1.4,
        driver_state="distracted",
        speed_mps=18.0,
        lane_offset_m=0.2,
    )
    assert result.severity == 5
    assert result.explanation_codes == ["short_ttc", "driver_distraction", "compound_risk"]
```

Add coaching tests proving critical driving does not generate verbose text and
the same idempotency key is not delivered twice.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --package fleetiq-fusion-worker pytest services/fusion-worker/tests -v`

Run: `uv run --package fleetiq-coaching-worker pytest services/coaching-worker/tests -v`

Expected: FAIL because the packages do not exist.

- [ ] **Step 3: Implement deterministic scoring and adapters**

Implement the approved category weights and severity modifiers. Provide
`MockCarSkyAdapter` and `CarSkyAdapter`. Require
`CARSKY_BASE_URL`, `CARSKY_API_KEY`, `CARSKY_ROOM_ID`, and
`CARSKY_NODE_KEY` only for the real adapter. Redact secrets and cap each request
with explicit connect/read timeouts.

- [ ] **Step 4: Run worker tests**

Run: `uv run --package fleetiq-fusion-worker pytest services/fusion-worker/tests -v`

Run: `uv run --package fleetiq-coaching-worker pytest services/coaching-worker/tests -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add services/fusion-worker services/coaching-worker
git commit -m "feat: add risk fusion and coaching workers"
```

### Task 11: Next.js Fleet Dashboard

**Files:**
- Create: `package.json`
- Create: `pnpm-lock.yaml`
- Create: `apps/web/README.md`
- Create: `apps/web/Dockerfile`
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/trips/[tripId]/page.tsx`
- Create: `apps/web/src/components/fleet-overview.tsx`
- Create: `apps/web/src/components/trip-live-view.tsx`
- Create: `apps/web/src/components/risk-timeline.tsx`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/camera-socket.ts`
- Create: `apps/web/src/lib/contracts.ts`
- Create: `apps/web/src/__tests__/fleet-overview.test.tsx`
- Create: `apps/web/src/__tests__/camera-socket.test.ts`

**Interfaces:**
- Consumes: FastAPI `/api/v1` and WSS endpoints.
- Produces: fleet overview, driver/trip ranking, synchronized trip live view, risk timeline, evidence panel and coaching report.

- [ ] **Step 1: Scaffold Next.js App Router with TypeScript**

Set the root `package.json` to `private: true`, pin the pnpm package manager,
provide `web:lint`, `web:typecheck`, `web:test`, and `web:build` scripts, and
add `aws-cdk` as a root development dependency for Task 14. Use pnpm for the
Next.js app and enable standalone output:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 2: Write failing component and socket tests**

```tsx
it("shows the highest-risk trip first", async () => {
  render(<FleetOverview trips={[safeTrip, riskyTrip]} />);
  expect(screen.getAllByTestId("trip-card")[0]).toHaveTextContent("T06-Sample");
});
```

The socket test must build and decode the same 4-byte metadata-length frame
protocol as FastAPI.

- [ ] **Step 3: Run tests and verify failure**

Run: `pnpm --filter @fleetiq/web test`

Expected: FAIL before components and socket decoder are implemented.

- [ ] **Step 4: Implement operational dashboard screens**

Use real FleetIQ labels and evidence fields. The first screen is the fleet
operations dashboard, not a marketing landing page. Show degraded/mock model
state visibly.

- [ ] **Step 5: Run frontend quality gates**

Run: `pnpm --filter @fleetiq/web lint`

Run: `pnpm --filter @fleetiq/web typecheck`

Run: `pnpm --filter @fleetiq/web test`

Run: `pnpm --filter @fleetiq/web build`

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```powershell
git add package.json pnpm-lock.yaml pnpm-workspace.yaml apps/web
git commit -m "feat: add FleetIQ Next.js operations dashboard"
```

### Task 12: CarSky Android Automotive HMI

**Files:**
- Create: `apps/carsky-hmi/README.md`
- Create: `apps/carsky-hmi/Dockerfile`
- Create: `apps/carsky-hmi/settings.gradle.kts`
- Create: `apps/carsky-hmi/build.gradle.kts`
- Create: `apps/carsky-hmi/app/build.gradle.kts`
- Create: `apps/carsky-hmi/app/src/main/AndroidManifest.xml`
- Create: `apps/carsky-hmi/app/src/main/java/io/fleetiq/hmi/MainActivity.kt`
- Create: `apps/carsky-hmi/app/src/main/java/io/fleetiq/hmi/CoachingViewModel.kt`
- Create: `apps/carsky-hmi/app/src/test/java/io/fleetiq/hmi/CoachingViewModelTest.kt`
- Create: `apps/carsky-hmi/carsky/blueprint.example.json`
- Create: `apps/carsky-hmi/carsky/bridge/README.md`
- Create: `apps/carsky-hmi/carsky/bridge/bridge.py`
- Create: `docs/runbooks/carsky-deploy.md`

**Interfaces:**
- Consumes: KUKSA/VSS or CarSky REST bridge coaching signal.
- Produces: safe Android Automotive coaching card and acknowledgement state.

- [ ] **Step 1: Write the view-model test**

```kotlin
@Test
fun criticalCommandUsesShortSafetyCopy() {
    val state = CoachingViewModel.reduce(
        CoachingState.Empty,
        CoachingCommand(severity = 5, title = "Brake", message = "Brake now")
    )
    assertEquals("Brake now", state.message)
    assertFalse(state.allowLongExplanation)
}
```

- [ ] **Step 2: Implement the minimum Android Automotive screen**

Render severity, one action phrase, acknowledgement status and connectivity.
Do not render raw model probabilities while driving. Keep report detail in the
web dashboard.

- [ ] **Step 3: Define the CarSky topology**

The example blueprint must identify Container Node, bridge pins, Skycraft
Android guest, VHAL/KUKSA signal and Screen widget. The runbook must document
Zot image push, artifact registration, Blueprint deployment, Room lookup,
device attachment and rollback to the mock adapter.

- [ ] **Step 4: Run available HMI validation**

Run: `docker build -f apps/carsky-hmi/Dockerfile apps/carsky-hmi`

Expected: APK builder image succeeds when Android dependencies are available.
If the organizer environment blocks dependency download, validate Gradle files
and record the exact external prerequisite in the README; do not mark the APK
build as passed.

- [ ] **Step 5: Commit**

```powershell
git add apps/carsky-hmi docs/runbooks/carsky-deploy.md
git commit -m "feat: scaffold CarSky Android coaching HMI"
```

### Task 13: Dockerfiles and Local Compose

**Files:**
- Create: `compose.yaml`
- Create: `.env.example`
- Create: `infra/compose/README.md`
- Create: `infra/compose/mosquitto.conf`
- Create: `infra/compose/postgres/init.sql`
- Create: `infra/docker/python-service.Dockerfile`
- Create: `infra/docker/model-mock/Dockerfile`
- Create: `infra/docker/model-mock/app.py`
- Create: `infra/compose/smoke_test.py`
- Modify: every application and service Dockerfile

**Interfaces:**
- Consumes: all deployable apps and workers.
- Produces: `core`, `perception`, and `full` Compose profiles with health checks.

- [ ] **Step 1: Write the Compose smoke test**

The test must:

1. GET API readiness.
2. Publish one telemetry event to Mosquitto.
3. Submit one local inference job.
4. Receive one risk event.
5. Connect to the camera WebSocket and decode one JPEG frame.
6. Receive one mock CarSky acknowledgement.

- [ ] **Step 2: Validate Compose before implementation**

Run: `docker compose config`

Expected: FAIL because `compose.yaml` does not exist.

- [ ] **Step 3: Implement multi-stage images and profiles**

Use health conditions instead of startup sleeps. Mount `data` and `artifacts`
read-only/read-write as appropriate. Do not bake either directory into an
image. Use internal Docker networks for database, Redis and Mosquitto.

- [ ] **Step 4: Validate and build**

Run: `docker compose config`

Run: `docker compose --profile core build`

Run: `docker compose --profile full build`

Expected: config and builds exit 0, except the separately documented Android
builder prerequisite from Task 12.

- [ ] **Step 5: Run the full smoke path**

Run: `docker compose --profile full up -d`

Run: `uv run python infra/compose/smoke_test.py`

Run: `docker compose --profile full down`

Expected: smoke test exits 0 and reports each of the six checks.

- [ ] **Step 6: Commit**

```powershell
git add compose.yaml .env.example infra/compose infra/docker apps services
git commit -m "build: add local FleetIQ Docker topology"
```

### Task 14: AWS ECS EC2, SageMaker, and IoT Infrastructure

**Files:**
- Create: `infra/aws/README.md`
- Create: `infra/aws/pyproject.toml`
- Create: `infra/aws/app.py`
- Create: `infra/aws/fleetiq_infra/__init__.py`
- Create: `infra/aws/fleetiq_infra/network_stack.py`
- Create: `infra/aws/fleetiq_infra/data_stack.py`
- Create: `infra/aws/fleetiq_infra/compute_stack.py`
- Create: `infra/aws/fleetiq_infra/ml_stack.py`
- Create: `infra/aws/fleetiq_infra/iot_stack.py`
- Create: `infra/aws/tests/conftest.py`
- Create: `infra/aws/tests/test_template.py`
- Create: `docs/runbooks/aws-deploy.md`

**Interfaces:**
- Consumes: container image URIs, SageMaker model artifact URIs, DNS/TLS configuration and secret references.
- Produces: synthesized CloudFormation for VPC, ALB, ECS EC2 capacity/services, S3, PostgreSQL/Redis configuration, SageMaker endpoints, IoT policies and CloudWatch logs.

- [ ] **Step 1: Write failing CDK template assertions**

Use these stack interfaces:

```python
NetworkStack(scope, stack_id, *, environment_name: str)
DataStack(scope, stack_id, *, vpc, environment_name: str)
MlStack(scope, stack_id, *, vpc, artifacts_bucket, environment_name: str)
IoTStack(scope, stack_id, *, environment_name: str)
ComputeStack(
    scope,
    stack_id,
    *,
    vpc,
    artifacts_bucket,
    database_secret,
    redis_endpoint: str,
    endpoint_arns: dict[str, str],
    environment_name: str,
)
```

`tests/conftest.py` creates an `App`, instantiates these stacks in dependency
order, and returns `Template.from_stack(compute_stack)` as the `template`
fixture. Then assert:

```python
from aws_cdk.assertions import Match


def test_compute_uses_ec2_capacity_and_sagemaker_permissions(template) -> None:
    template.resource_count_is("AWS::ECS::Cluster", 1)
    template.has_resource_properties(
        "AWS::ECS::Service",
        {"LaunchType": "EC2"},
    )
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {"PolicyDocument": {"Statement": Match.array_with([
            Match.object_like({"Action": "sagemaker:InvokeEndpoint"})
        ])}},
    )
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --package fleetiq-infra pytest infra/aws/tests -v`

Expected: FAIL because stacks do not exist.

- [ ] **Step 3: Implement least-privilege stacks**

Use private subnets for ECS tasks, database and Redis. Expose only ALB
HTTPS/WSS. Restrict ECS IAM to named SageMaker endpoints and S3 prefixes.
Reference secrets by ARN. Tag every resource with `Project=FleetIQ` and
`Environment`.

- [ ] **Step 4: Synthesize without deploying**

Run: `uv run --package fleetiq-infra pytest infra/aws/tests -v`

Run: `pnpm exec cdk synth --app "uv run --package fleetiq-infra python infra/aws/app.py"`

Expected: tests pass and CloudFormation is synthesized locally. Do not run
`cdk deploy`.

- [ ] **Step 5: Commit**

```powershell
git add infra/aws docs/runbooks/aws-deploy.md
git commit -m "infra: define ECS EC2 and SageMaker deployment"
```

### Task 15: Artifact Migration, Documentation, and Breaking-Refactor Gate

**Files:**
- Move: `UchiHahaha-Hackathon2026.pptx` -> `docs/proposal/UchiHahaha-Hackathon2026.pptx`
- Move: `UchiHahaha-Hackathon2026.pdf` -> `docs/proposal/UchiHahaha-Hackathon2026.pdf`
- Move: organizer PDF/PPTX references -> `docs/reference/organizer/`
- Move: `docs/Car-Sky-Platform.html` and `docs/Digital-Cockpit.html` -> `docs/reference/carsky/`
- Move: `docs/diagrams/` -> `docs/architecture/diagrams/`
- Move: progress one-pager/PDF -> `docs/reports/progress/`
- Move local-only: `paper/` -> `research/papers/raw/`
- Move local-only: `third_party/` -> `research/third-party/`
- Move local-only: root model weights -> `artifacts/models/checkpoints/`
- Reclassify local-only: current `artifacts/*` into the approved subdirectories
- Create: `docs/README.md`
- Create: `docs/architecture/README.md`
- Create: `docs/proposal/README.md`
- Create: `docs/reference/README.md`
- Create: `docs/reports/README.md`
- Create: `docs/runbooks/README.md`
- Create: `docs/architecture/system.md`
- Create: `docs/architecture/repository.md`
- Modify: `README.md`
- Modify: all Markdown links affected by moves
- Modify: `tests/architecture/test_repository_skeleton.py`
- Delete: `main.py`
- Delete: empty legacy `scripts/` directories

**Interfaces:**
- Consumes: all completed applications, services, packages, infrastructure and local artifacts.
- Produces: contributor onboarding, command migration table, correctly classified repository content and a hard no-legacy gate.

- [ ] **Step 1: Extend the architecture test with breaking-refactor assertions**

```python
def test_legacy_roots_are_removed() -> None:
    assert not (ROOT / "scripts").exists()
    assert not (ROOT / "notebooks").exists()
    assert not (ROOT / "main.py").exists()


def test_tracked_code_has_no_legacy_imports() -> None:
    import subprocess

    offenders = []
    tracked = subprocess.check_output(
        ["git", "ls-files", "*.py"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for relative in tracked:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        if "scripts.roadface" in text or "from scripts" in text:
            offenders.append(relative)
    assert offenders == []
```

- [ ] **Step 2: Run the architecture test and verify failure**

Run: `uv run pytest tests/architecture/test_repository_skeleton.py -v`

Expected: FAIL while legacy paths still exist.

- [ ] **Step 3: Verify move targets before moving local-only directories**

Use `Resolve-Path` on each source and parent target. Confirm every resolved
target remains under the repository root. Use PowerShell `Move-Item
-LiteralPath` end-to-end; do not pass generated path lists to another shell.

- [ ] **Step 4: Move tracked and ignored content**

Use `git mv` for tracked files. Use native PowerShell moves for ignored local
weights, papers, clones and generated artifacts. Preserve all three untracked
team-report files by moving them into `docs/reports/progress/` rather than
deleting or overwriting them.

- [ ] **Step 5: Rewrite root onboarding**

The root README must include:

- 30-second project explanation.
- Architecture and protocol overview.
- Exact prerequisites.
- `uv`, pnpm and Docker Compose quick starts.
- Dataset placement.
- Common training, relabeling, visualization and service commands.
- Old-to-new command migration table.
- AWS and CarSky runbook links.
- Team ownership boundaries.
- Generated-artifact and secret policy.

- [ ] **Step 6: Run all repository gates**

Run: `uv lock --check`

Run: `uv run pytest -v`

Run: `pnpm --filter @fleetiq/web lint`

Run: `pnpm --filter @fleetiq/web typecheck`

Run: `pnpm --filter @fleetiq/web test`

Run: `pnpm --filter @fleetiq/web build`

Run: `docker compose config`

Run: `git diff --check`

Run: `rg -n "scripts[./\\\\]roadface|from scripts|import scripts" --glob "!docs/superpowers/**" .`

Expected: all test/build/config commands exit 0 and the legacy reference audit
returns no matches.

- [ ] **Step 7: Verify ignored content and Git status**

Run: `git check-ignore data/Practice_Dataset artifacts/models research/papers/raw research/third-party .superpowers`

Run: `git status --short`

Expected: local-only roots are ignored. Git status contains only intentional
refactor changes and preserved user files in their approved documentation
targets.

- [ ] **Step 8: Commit**

```powershell
git add -A
git commit -m "refactor: complete FleetIQ deployable monorepo"
```

---

## Final Verification Matrix

| Area | Required evidence |
| --- | --- |
| Repository | Architecture tests pass; no `scripts/roadface` references |
| Python | `uv lock --check` and complete pytest suite pass |
| Road-facing | Existing lane and LocateAnything tests pass at new imports |
| Contracts | JSON Schema export and round-trip tests pass |
| API | HTTP and WebSocket tests pass |
| Events | MQTT handler and Compose publish/subscribe pass |
| SageMaker | boto3 contract tests and local fixtures pass |
| DMS/Fusion | smoothing, compound-risk and scoring tests pass |
| Frontend | lint, typecheck, unit tests and production build pass |
| CarSky | blueprint/runbook validation; APK build status reported truthfully |
| Containers | Compose config, builds, health checks and smoke path pass |
| AWS | CDK tests and `cdk synth` pass; no deployment is performed |
| Assets | ignored status preserved after every local move |

## Rollback Boundaries

Each task is a separate commit. If a task fails review, revert only that task's
commit and preserve earlier package boundaries. Do not use `git reset --hard`.
Tasks 4 and 5 form the road-facing breaking boundary and must be reverted
together if either leaves runtime imports unresolved. Task 15 is the only task
that removes legacy roots and moves large local-only artifacts.
