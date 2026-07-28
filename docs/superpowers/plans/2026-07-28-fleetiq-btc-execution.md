# FleetIQ Guardian BTC Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver and demonstrate the organizer-approved C1-C3 FleetIQ vertical slice by 2026-08-08, with standardized project structure, Road-facing risk, stereo depth, vehicle dynamics, DMS, risk fusion, CarSky Android IVI coaching, KPIs, and reproducible demo artifacts.

**Architecture:** Existing experiments remain under `scripts/roadface`, while stable cross-team interfaces move into an installable `src/fleetiq` package. Every producer emits versioned contracts; an orchestrator aligns road, driver, and vehicle signals, creates risk events, applies a deterministic safety gate, and sends coaching through mock or real CarSky adapters.

**Tech Stack:** Python 3.12, uv, dataclasses, NumPy, OpenCV/StereoSGBM, PyTorch/timm, PyYAML, FastAPI/uvicorn, httpx, pytest, Ruff, GitHub Actions, CarSky REST API, KUKSA/VSS, Android Automotive Skycraft VM.

## Global Constraints

- C1 recovery demo due 2026-07-29.
- C2 platform demo and initial KPIs due 2026-08-03.
- C3 code freeze due 2026-08-08; final submission is 2026-08-10.
- Python remains `>=3.12,<3.13`; dependencies are locked with `uv.lock`.
- Dataset, model weights, credentials, videos, and generated artifacts must not be committed.
- CPU unit/contract tests block pull requests; GPU and CarSky tests are opt-in.
- No component may issue steering, braking, throttle, or other vehicle-control commands.
- Missing measurements remain `None`/invalid with a reason; no module fabricates confidence or depth.
- Every issue is owned by one GitHub assignee, estimated at two to eight hours, and linked to its dependencies.
- CarSky secrets use `CARSKY_BASE_URL`, `CARSKY_API_KEY`, `CARSKY_ROOM_ID`, and `CARSKY_NODE_KEY`.

---

## File Map

```text
src/fleetiq/
  common/config.py             YAML/env loading and validation
  common/logging.py            structured run logs
  common/artifacts.py          run directory and metadata
  contracts/models.py          canonical JSON-safe dataclasses
  contracts/serialization.py   schema-versioned JSONL
  roadface/adapter.py          legacy pipeline adapter
  geometry/stereo.py           disparity, depth and confidence
  geometry/horizon.py          IMU-aware horizon
  vehicle/dynamics.py          filtering and fast-corner detector
  vehicle/trajectory.py        world-path builder
  dms/adapter.py               DMS protocol and stub
  dms/model.py                 ConvNeXt-tiny state classifier
  dms/smoothing.py             temporal state filter
  fusion/alignment.py          timestamp/frame alignment
  fusion/rules.py              compound-risk rules and score
  fusion/safety_gate.py        intervention eligibility
  coaching/policy.py           event-to-message mapping
  carsky/client.py             REST client
  carsky/adapters.py           mock and real adapters
  demo/runner.py               end-to-end orchestration
  demo/__main__.py             standard CLI
  visualization/trajectory.py  trip map rendering
  visualization/overlay.py     evidence overlay
configs/
  demo.yaml
  risk_thresholds.yaml
  coaching_templates.yaml
  dms_baseline.yaml
tests/
  unit/
  contract/
  integration/
.github/
  workflows/ci.yml
  ISSUE_TEMPLATE/task.yml
  pull_request_template.md
  CODEOWNERS
```

## Stable Interfaces

```python
class RoadfaceAdapter:
    def analyze(self, frame: FrameContext) -> tuple[RoadRiskSignal, ...]: ...

class DmsAdapter:
    def analyze(self, frame: FrameContext) -> DriverStateSignal: ...

class FastCornerDetector:
    def update(self, state: VehicleStateSignal) -> tuple[RiskEvent, ...]: ...

class TimeAligner:
    def align(
        self,
        frame: FrameContext,
        road: tuple[RoadRiskSignal, ...],
        driver: DriverStateSignal,
        vehicle: VehicleStateSignal,
    ) -> AlignedFrame: ...

class RiskFusion:
    def evaluate(self, frame: AlignedFrame) -> tuple[RiskEvent, ...]: ...

class SafetyGate:
    def evaluate(
        self, event: RiskEvent, vehicle: VehicleStateSignal, now_ms: int
    ) -> GateDecision: ...

class CoachingPolicy:
    def command_for(self, event: RiskEvent) -> CoachingCommand | None: ...

class CarSkyAdapter:
    def send(self, command: CoachingCommand) -> DeliveryReceipt: ...

def run_demo(config: DemoConfig) -> RunSummary: ...
```

## Milestone and Capacity Summary

| Gate | Tư | Phi | Trung | Kha | Dũng | Total |
|---|---:|---:|---:|---:|---:|---:|
| C1 | 10h | 10h | 8h | 8h | 6h | 42h |
| C2 | 26h | 30h | 20h | 26h | 18h | 120h |
| C3 | 16h | 18h | 16h | 20h | 18h | 88h |
| **Total** | **52h** | **58h** | **44h** | **54h** | **42h** | **250h** |

## Dependency Chain

```text
C1-02 contracts/fusion skeleton
  -> C1-03 package/config
  -> C1-04 Road adapter
  -> C1-05 DMS stub
  -> C1-06 frozen Road sample
  -> C1-07 skeleton demo

C1-07
  -> C2 standardization/API
  -> stereo/depth/horizon
  -> real DMS
  -> vehicle dynamics/trajectory
  -> time alignment/fusion
  -> coaching policy
  -> CarSky integration
  -> C2 demo

C2 acceptance
  -> six-trip evaluation/tuning
  -> reliability and frozen manifests
  -> three clean demo runs
  -> video/pitch/submission
```

---

## C0/C1 Recovery Tasks

### Task 1: C1-01 Scope, Risk Register, and Progress Package

**Owner:** Dũng (`VKUNeMo`)  
**Gate / Estimate / Priority:** C1 / 6h / P0  
**Dependencies:** None

**Files:**
- Modify: `docs/TEAM_PROGRESS_ONEPAGER.md`
- Create: `docs/C0_SCOPE_AND_RISKS.md`
- Create: `docs/demo/C1_DEMO_SCRIPT.md`

**Produces:** Organizer-ready C0 scope page, C1 progress page, and five-minute script.

- [ ] Verify must-have, nice-to-have, stack, resources, five risks, owners, and C1 evidence are present.
- [ ] Add a 300-second script with timestamps and explicit labels for real versus stub output.
- [ ] Run `rg -n "TBD|TODO" docs/C0_SCOPE_AND_RISKS.md docs/demo/C1_DEMO_SCRIPT.md`; expect no matches.
- [ ] Commit with `git commit -m "docs: add C0 scope and C1 demo package"`.

### Task 2: C1-02 Canonical Contracts and Fusion Skeleton

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C1 / 8h / P0  
**Dependencies:** None

**Files:**
- Create: `src/fleetiq/contracts/models.py`
- Create: `src/fleetiq/contracts/serialization.py`
- Create: `src/fleetiq/fusion/alignment.py`
- Create: `src/fleetiq/fusion/rules.py`
- Test: `tests/contract/test_signal_contracts.py`
- Test: `tests/unit/test_fusion_skeleton.py`

**Produces:** Dataclasses in the approved spec, JSONL round-trip, `TimeAligner.align`, and deterministic stub `RiskFusion.evaluate`.

- [ ] Write contract tests for enum validation, nullable measurements, JSON round-trip, and rejected schema versions.
- [ ] Run `uv run pytest tests/contract/test_signal_contracts.py -q`; expect failure because modules do not exist.
- [ ] Implement schema version `1.0`, finite-number sanitization, and one compound rule: distracted/drowsy plus short TTC.
- [ ] Run `uv run pytest tests/contract/test_signal_contracts.py tests/unit/test_fusion_skeleton.py -q`; expect pass.
- [ ] Commit with `git commit -m "feat: define canonical risk contracts"`.

### Task 3: C1-03 Package, Config, Artifacts, and Demo CLI Skeleton

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C1 / 6h / P0  
**Dependencies:** C1-02

**Files:**
- Modify: `pyproject.toml`
- Create: `src/fleetiq/common/config.py`
- Create: `src/fleetiq/common/artifacts.py`
- Create: `src/fleetiq/demo/__main__.py`
- Create: `configs/demo.yaml`
- Test: `tests/unit/test_config.py`
- Test: `tests/integration/test_demo_cli.py`

**Produces:** Installable package and `python -m fleetiq.demo --trip ... --adapter mock`.

- [ ] Write tests for required config keys, environment overrides, run directory naming, and CLI exit codes.
- [ ] Run `uv run pytest tests/unit/test_config.py tests/integration/test_demo_cli.py -q`; expect failure.
- [ ] Add `pyyaml`, package discovery, `DemoConfig`, `create_run_dir`, and an argparse CLI that emits `run_metadata.json`.
- [ ] Run the tests and `uv run python -m fleetiq.demo --help`; expect pass and exit code 0.
- [ ] Commit with `git commit -m "feat: add standard demo package and CLI"`.

### Task 4: C1-04 Legacy Road-facing Contract Adapter

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C1 / 6h / P0  
**Dependencies:** C1-02

**Files:**
- Create: `src/fleetiq/roadface/adapter.py`
- Modify: `scripts/roadface/run_roadface_pipeline.py`
- Test: `tests/contract/test_roadface_adapter.py`

**Consumes / Produces:** Existing CSV/JSONL/KITTI outputs -> `tuple[RoadRiskSignal, ...]`.

- [ ] Write fixtures for valid detections, missing depth, infinite TTC, duplicate tracks, and out-of-path targets.
- [ ] Run `uv run pytest tests/contract/test_roadface_adapter.py -q`; expect failure.
- [ ] Implement `LegacyRoadfaceAdapter` without changing existing model behavior; preserve source and confidence fields.
- [ ] Run adapter tests plus existing `tests/test_carnd_lane_tracker.py` and `tests/test_locateanything_labels.py`.
- [ ] Commit with `git commit -m "feat: adapt roadface output to canonical signals"`.

### Task 5: C1-05 DMS Taxonomy and Deterministic Stub

**Owner:** Trung (`hoangtrung1801`)  
**Gate / Estimate / Priority:** C1 / 8h / P0  
**Dependencies:** C1-02

**Files:**
- Create: `src/fleetiq/dms/adapter.py`
- Create: `configs/dms_baseline.yaml`
- Test: `tests/contract/test_dms_adapter.py`

**Produces:** `DmsAdapter` protocol, label mapping, and `LabelBackedDmsAdapter`.

- [ ] Write mapping tests: `alert -> attentive`, `distracted -> distracted`, `drowsy/yawning/microsleep -> drowsy`, missing/low confidence -> `unknown`.
- [ ] Run `uv run pytest tests/contract/test_dms_adapter.py -q`; expect failure.
- [ ] Implement the adapter using frame-level JSON labels and mark output source as `label_stub`.
- [ ] Run tests and export one 600-frame DMS JSONL sequence for the C1 demo.
- [ ] Commit with `git commit -m "feat: add normalized DMS stub adapter"`.

### Task 6: C1-06 Frozen Road Sample and Evidence

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C1 / 4h / P0  
**Dependencies:** C1-04

**Files:**
- Create: `configs/c1_demo.yaml`
- Create: `docs/demo/C1_EVIDENCE_MANIFEST.md`
- Modify: `scripts/roadface/visualize_roadface_outputs.py`

**Produces:** One deterministic trip/frame range with RoadRiskSignal JSONL and evidence references.

- [ ] Select a frame window containing a visible risk event and record why it is representative.
- [ ] Run the Road-facing pipeline twice with the same config and compare normalized JSONL hashes.
- [ ] Add an evidence manifest containing trip, frame range, config hash, model ID, known errors, and replay command.
- [ ] Commit with `git commit -m "test: freeze C1 road-facing evidence sample"`.

### Task 7: C1-07 Five-Minute Skeleton Demo Assembly

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C1 / 4h / P0  
**Dependencies:** C1-01, C1-02, C1-03, C1-04, C1-05, C1-06

**Files:**
- Create: `src/fleetiq/demo/runner.py`
- Create: `src/fleetiq/carsky/adapters.py`
- Test: `tests/integration/test_c1_skeleton.py`

**Produces:** Road signal + DMS stub + fusion event + mock coaching receipt in one run.

- [ ] Write an integration test asserting one `RiskEvent`, one `CoachingCommand`, one mock `DeliveryReceipt`, and explicit stub source labels.
- [ ] Run `uv run pytest tests/integration/test_c1_skeleton.py -q`; expect failure.
- [ ] Implement `MockCarSkyAdapter` and `run_demo` using dependency-injected adapters.
- [ ] Run the C1 test and the five-minute replay command; attach evidence to the C1 milestone issue.
- [ ] Commit with `git commit -m "feat: assemble C1 end-to-end skeleton"`.

---

## C2 Midterm Tasks

### Task 8: C2-01 CI, Dev Tooling, Templates, and Event API

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C2 / 8h / P0  
**Dependencies:** C1-07

**Files:**
- Modify: `pyproject.toml`
- Create: `.github/workflows/ci.yml`
- Create: `.github/ISSUE_TEMPLATE/task.yml`
- Create: `.github/pull_request_template.md`
- Create: `.github/CODEOWNERS`
- Create: `src/fleetiq/demo/event_api.py`
- Test: `tests/integration/test_event_api.py`

**Produces:** CPU CI and local read-only endpoints for run summary, events, trajectory, and coaching receipts.

- [ ] Write API contract tests for `GET /health`, `/runs/{id}`, `/events`, and `/trajectory`.
- [ ] Add `dev` dependencies (pytest, ruff, coverage) and API dependencies (FastAPI, uvicorn); run tests first and expect missing modules.
- [ ] Implement the minimal read-only API and GitHub workflow running Ruff plus CPU tests on Python 3.12.
- [ ] Run `uv run ruff check .` and `uv run pytest -q`; commit with `git commit -m "build: add CI and event API"`.

### Task 9: C2-02 CarSky Access, Blueprint, and Signal Contract

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C2 / 8h / P0  
**Dependencies:** C1-07

**Files:**
- Create: `carsky/fleetiq-blueprint.json`
- Create: `docs/CARSKY_DEPLOYMENT.md`
- Create: `.env.example`
- Test: `tests/contract/test_carsky_signal_payload.py`

**Produces:** Container Node + KUKSA/VSS or signal node + Skycraft AAOS topology and exact signal payload.

- [ ] Define JSON payload paths for event type, severity, confidence, title, message, expiry, and dedupe key.
- [ ] Add tests ensuring no secret is serialized and all actuation payloads are coaching/display-only.
- [ ] Validate `GET /api/v1/healthz`, room deployment status, signal node discovery, and AAOS screenshot manually.
- [ ] Document rollback, mock fallback, `X-API-Key` auth, and commit with `git commit -m "feat: define CarSky FleetIQ blueprint"`.

### Task 10: C2-03 Real CarSky REST Adapter

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-02

**Files:**
- Create: `src/fleetiq/carsky/client.py`
- Modify: `src/fleetiq/carsky/adapters.py`
- Test: `tests/integration/test_carsky_adapter.py`

**Consumes / Produces:** `CoachingCommand` -> `DeliveryReceipt`.

- [ ] Mock `GET /api/v1/signals/{roomId}` and `POST /api/v1/signals/{roomId}/{nodeKey}/actuate`.
- [ ] Test `X-API-Key`, timeout, 401/403, 429/5xx retry policy, dedupe, and mock fallback.
- [ ] Add `httpx`, then implement `CarSkyClient` with bounded timeout/retries and redact secrets from logs.
- [ ] Run adapter tests and one opt-in live smoke request; commit with `git commit -m "feat: send coaching commands to CarSky"`.

### Task 11: C2-04 Trajectory API and Demo Panel Integration

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C2 / 4h / P1  
**Dependencies:** C2-01, C2-14

**Files:**
- Create: `src/fleetiq/visualization/trajectory.py`
- Modify: `scripts/render_trip_dashboard.py`
- Test: `tests/integration/test_trajectory_render.py`

**Produces:** PNG and JSON trajectory artifacts for each requested trip.

- [ ] Write a headless render test asserting non-empty image, equal-axis bounds, speed legend, and event markers.
- [ ] Implement speed-colored line segments, acceleration-scaled markers, heading arrows, and event labels.
- [ ] Render all six trips and assert six PNG plus six JSON artifacts exist.
- [ ] Commit with `git commit -m "feat: visualize speed-colored trip trajectories"`.

### Task 12: C2-05 Stereo Depth Core

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C2 / 8h / P0  
**Dependencies:** C1-03

**Files:**
- Create: `src/fleetiq/geometry/stereo.py`
- Modify: `scripts/roadface/roadface_lib.py`
- Test: `tests/unit/test_stereo_depth.py`

**Produces:** `StereoDepthEstimator.estimate(left, right, calibration)`.

- [ ] Write synthetic rectified-pair tests verifying `depth = fx * baseline / disparity`.
- [ ] Run tests and expect failure before implementation.
- [ ] Refactor SGBM into the geometry package; reject non-positive disparity, depths outside 0.5-90 m, and invalid calibration.
- [ ] Run unit tests plus a T01 frame smoke test; commit with `git commit -m "feat: add calibrated stereo depth estimator"`.

### Task 13: C2-06 Stereo Confidence and Object ROI Distance

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-05

**Files:**
- Modify: `src/fleetiq/geometry/stereo.py`
- Create: `src/fleetiq/geometry/object_depth.py`
- Test: `tests/unit/test_stereo_confidence.py`

**Produces:** Left-right consistency mask, confidence artifact, and robust object distance.

- [ ] Write tests for occlusion, textureless patches, sky/no-hit, sparse valid pixels, and ROI boundary clipping.
- [ ] Implement reverse matching, consistency threshold, confidence normalization, ROI erosion, and robust lower-center quantiles.
- [ ] Assert invalid regions remain invalid rather than filled.
- [ ] Run tests and commit with `git commit -m "feat: add stereo confidence and object depth"`.

### Task 14: C2-07 Stereo-vs-GT Benchmark

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-05, C2-06

**Files:**
- Create: `scripts/evaluate_stereo_depth.py`
- Create: `tests/integration/test_stereo_benchmark.py`
- Create: `docs/metrics/STEREO_DEPTH_C2.md`

**Produces:** Per-trip coverage, median/mean AE, AbsRel, and rain/night breakdown.

- [ ] Freeze the evaluation protocol: GT frames every 5 frames, rows 90-359, GT range 0.5-90 m.
- [ ] Add a deterministic five-frame smoke benchmark test with upper bounds based on the audited baseline.
- [ ] Run all 720 GT frames or document the exact sampled fallback if runtime exceeds the gate budget.
- [ ] Commit metric JSON/Markdown only, not depth arrays, with `git commit -m "test: benchmark stereo depth on practice trips"`.

### Task 15: C2-08 IMU-Aware Horizon

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C2 / 6h / P1  
**Dependencies:** C2-05

**Files:**
- Create: `src/fleetiq/geometry/horizon.py`
- Test: `tests/unit/test_horizon.py`
- Create: `docs/metrics/HORIZON_C2.md`

**Produces:** `estimate_horizon(K, pitch, roll, imu_to_camera) -> HorizonEstimate`.

- [ ] Write analytic tests for zero attitude, positive/negative pitch, roll slope, identity extrinsics, and T03 3.37-degree pitch.
- [ ] Implement gravity projection `line = K^-T * gravity_camera`, mount-bias estimation, and low-pass filtering.
- [ ] Compare fixed and adjusted horizon against depth-supported road-plane residual and temporal jitter.
- [ ] Commit with `git commit -m "feat: compensate horizon using vehicle attitude"`.

### Task 16: C2-09 Road-facing Depth/Horizon/TTC Integration

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C2 / 4h / P0  
**Dependencies:** C2-06, C2-07, C2-08

**Files:**
- Modify: `src/fleetiq/roadface/adapter.py`
- Modify: `scripts/roadface/run_roadface_pipeline.py`
- Test: `tests/integration/test_roadface_depth_ttc.py`

**Produces:** One-trip real RoadRiskSignal sequence with depth source, confidence, ego-path flag, relative speed, and TTC.

- [ ] Add a replay test for GT-available, stereo-valid, and stereo-invalid fallback frames.
- [ ] Implement source precedence and preserve `depth_source`/quality in evidence.
- [ ] Verify horizon changes ROI without shifting labels or image coordinates.
- [ ] Run replay twice for deterministic event windows; commit with `git commit -m "feat: integrate stereo geometry into road risk"`.

### Task 17: C2-10 DMS Dataset and ConvNeXt-Tiny Baseline

**Owner:** Trung (`hoangtrung1801`)  
**Gate / Estimate / Priority:** C2 / 8h / P0  
**Dependencies:** C1-05

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/dms/prepare_dms_dataset.py`
- Create: `scripts/dms/train_dms.py`
- Modify: `configs/dms_baseline.yaml`
- Test: `tests/unit/test_dms_dataset.py`

**Produces:** Subject-grouped manifest and trained `timm` `convnext_tiny` four-state classifier.

- [ ] Test frame-label alignment, state mapping, subject grouping, deterministic splits, and no subject overlap.
- [ ] Generate manifests from 3,600 driver frames without copying images into Git-tracked paths.
- [ ] Add a `dms` optional dependency group for torch, torchvision, timm, Pillow, and scikit-learn; fine-tune ConvNeXt-tiny at 224 px with class weighting, early stopping, and fixed seed.
- [ ] Save weights under ignored artifacts and commit config/metrics with `git commit -m "feat: train DMS state baseline"`.

### Task 18: C2-11 Real DMS Inference Adapter

**Owner:** Trung (`hoangtrung1801`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-10

**Files:**
- Create: `src/fleetiq/dms/model.py`
- Modify: `src/fleetiq/dms/adapter.py`
- Test: `tests/contract/test_real_dms_adapter.py`

**Produces:** `PretrainedDmsAdapter.analyze` with four-state probabilities and `unknown` rejection.

- [ ] Write tests for preprocessing, probability sum, confidence threshold, missing frame, corrupt image, and CPU inference.
- [ ] Implement batched inference and model/config hash reporting.
- [ ] Preserve optional eye/head/mouth fields as `None` unless a model actually predicts them.
- [ ] Run tests and one full-trip inference; commit with `git commit -m "feat: add real DMS inference adapter"`.

### Task 19: C2-12 DMS Temporal Smoothing and Initial KPI

**Owner:** Trung (`hoangtrung1801`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-11

**Files:**
- Create: `src/fleetiq/dms/smoothing.py`
- Create: `scripts/dms/evaluate_dms.py`
- Create: `docs/metrics/DMS_C2.md`
- Test: `tests/unit/test_dms_smoothing.py`

**Produces:** Smoothed state sequence, macro-F1, per-state confusion matrix, and transitions/minute.

- [ ] Test minimum dwell, confidence hysteresis, `unknown`, and recovery to attentive.
- [ ] Evaluate with subject-grouped split and report sample counts plus leakage checks.
- [ ] Compare raw versus smoothed macro-F1 and transitions/minute.
- [ ] Commit code/metrics with `git commit -m "test: evaluate temporally smoothed DMS"`.

### Task 20: C2-13 Vehicle Telemetry Normalization and Filtering

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C1-02

**Files:**
- Create: `src/fleetiq/vehicle/dynamics.py`
- Test: `tests/unit/test_vehicle_dynamics.py`

**Produces:** `parse_vehicle_state` and a filtered 20 Hz VehicleStateSignal stream.

- [ ] Write tests for units, yaw unwrap, yaw rate, median/Hampel filtering, timestamp gaps, and physical outliers.
- [ ] Assert location-derived speed MAE remains within 0.02 m/s on Practice Dataset.
- [ ] Implement quality flags rather than silently clipping invalid data.
- [ ] Commit with `git commit -m "feat: normalize and filter vehicle dynamics"`.

### Task 21: C2-14 Fast-Corner Detector and Trajectory Builder

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-13

**Files:**
- Create: `src/fleetiq/vehicle/trajectory.py`
- Modify: `src/fleetiq/vehicle/dynamics.py`
- Create: `configs/risk_thresholds.yaml`
- Test: `tests/unit/test_fast_corner.py`
- Test: `tests/unit/test_trajectory.py`

**Produces:** `fast_corner` RiskEvent and TripTrajectory.

- [ ] Test 20 km/h minimum, 2.5/4.0 m/s² levels, 0.25-second dwell, braking overlap, hysteresis, cooldown, and one-frame outlier rejection.
- [ ] Test trajectory origin normalization, equal coordinates, speed/accel arrays, yaw, and event references.
- [ ] Tune against `behavior_flags.harsh_corner` and report event-window precision/recall plus false alerts/minute.
- [ ] Commit with `git commit -m "feat: detect fast corners and build trip trajectories"`.

### Task 22: C2-15 Production Time Alignment

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-09, C2-12, C2-13

**Files:**
- Modify: `src/fleetiq/fusion/alignment.py`
- Test: `tests/unit/test_time_alignment.py`

**Produces:** Complete `AlignedFrame` at 20 Hz with missing/stale flags.

- [ ] Test exact frame match, nearest 5 Hz GT depth, missing DMS frame, delayed Road output, and end-of-trip flush.
- [ ] Implement frame-index-first alignment and timestamp tolerance checks.
- [ ] Reject stale measurements rather than carrying them indefinitely.
- [ ] Run tests and commit with `git commit -m "feat: align multimodal trip signals"`.

### Task 23: C2-16 Compound Risk, Score, and Safety Gate

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C2 / 8h / P0  
**Dependencies:** C2-14, C2-15

**Files:**
- Modify: `src/fleetiq/fusion/rules.py`
- Create: `src/fleetiq/fusion/safety_gate.py`
- Test: `tests/unit/test_compound_risk.py`
- Test: `tests/unit/test_safety_gate.py`

**Produces:** Compound events, explainable trip score, and GateDecision.

- [ ] Test short TTC, fast corner, harsh brake, speeding, DMS-only, distracted+d TTC, stale event, dedupe, cooldown, and post-trip fallback.
- [ ] Implement transparent score impacts and recovery behavior from YAML thresholds.
- [ ] Ensure no real-time command is emitted for low-confidence or expired events.
- [ ] Run tests and commit with `git commit -m "feat: add compound risk scoring and safety gate"`.

### Task 24: C2-17 Safe Coaching Policy and Templates

**Owner:** Dũng (`VKUNeMo`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C1-02

**Files:**
- Create: `src/fleetiq/coaching/policy.py`
- Create: `configs/coaching_templates.yaml`
- Test: `tests/unit/test_coaching_policy.py`

**Produces:** Deterministic event-to-channel/template mapping.

- [ ] Write tests for TTC, distraction, drowsiness, fast corner, harsh brake, post-trip-only, unsupported event, and message expiry.
- [ ] Write short non-blaming Vietnamese and English templates with one action per real-time message.
- [ ] Implement channel/priority selection with no free-form LLM in the real-time critical path.
- [ ] Commit with `git commit -m "feat: define safety-gated coaching policy"`.

### Task 25: C2-18 NLP Coaching Summary Generator

**Owner:** Dũng (`VKUNeMo`)  
**Gate / Estimate / Priority:** C2 / 6h / P1  
**Dependencies:** C2-17, C2-16

**Files:**
- Create: `src/fleetiq/coaching/summary.py`
- Test: `tests/unit/test_coaching_summary.py`

**Produces:** Post-trip summary with exactly three evidence-linked actions.

- [ ] Test empty trip, repeated events, conflicting events, language selection, evidence IDs, and deterministic fallback.
- [ ] Implement ranked template composition; optional LLM rewriting is behind a flag and validated against the same facts.
- [ ] Reject output that introduces measurements or events absent from input.
- [ ] Commit with `git commit -m "feat: generate evidence-linked coaching summaries"`.

### Task 26: C2-19 IVI Content and Ten-Minute C2 Narrative

**Owner:** Dũng (`VKUNeMo`)  
**Gate / Estimate / Priority:** C2 / 6h / P0  
**Dependencies:** C2-17

**Files:**
- Create: `docs/demo/C2_DEMO_SCRIPT.md`
- Create: `docs/IVI_CONTENT_GUIDE.md`
- Create: `docs/metrics/C2_SCORECARD.md`

**Produces:** IVI content hierarchy, 600-second demo script, and KPI scorecard template.

- [ ] Define visual priority, maximum text length, dwell time, color, and non-interruption rules.
- [ ] Map each demo moment to a real command, screen evidence, owner, and fallback.
- [ ] Include Road, stereo, DMS, fast-corner, Fusion, CarSky, and KPI sections inside ten minutes.
- [ ] Commit with `git commit -m "docs: prepare C2 IVI content and demo narrative"`.

---

## C3 Code Freeze Tasks

### Task 27: C3-01 Clean Replay Package and Frozen Manifest

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C3 / 6h / P0  
**Dependencies:** C2-01 through C2-19

**Files:**
- Create: `scripts/verify_release.py`
- Create: `configs/frozen_demo.yaml`
- Create: `docs/RELEASE_MANIFEST.md`
- Test: `tests/integration/test_frozen_replay.py`

**Produces:** Config/model/data hashes and one-command replay from a clean process.

- [ ] Test manifest completeness, ignored artifact paths, config hash, model ID, and missing-file diagnostics.
- [ ] Run CPU tests, opt-in GPU smoke, and mock replay from a fresh shell.
- [ ] Record exact commands and expected artifact list.
- [ ] Commit with `git commit -m "release: freeze reproducible demo manifest"`.

### Task 28: C3-02 CarSky Reliability and Latency

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C3 / 6h / P0  
**Dependencies:** C2-03, C2-16, C2-17

**Files:**
- Modify: `src/fleetiq/carsky/client.py`
- Create: `scripts/benchmark_carsky_delivery.py`
- Create: `docs/metrics/CARSKY_C3.md`
- Test: `tests/integration/test_carsky_reliability.py`

**Produces:** At least 20-command replay, delivery rate, p50/p95 latency, retries, and duplicate suppression.

- [ ] Add tests for network loss, delayed response, duplicate command, expired command, and room unavailable.
- [ ] Run live benchmark targeting at least 95% delivery and p95 at or below 1,000 ms.
- [ ] If live access fails, attach the exact failure and run mock reliability without claiming live KPI.
- [ ] Commit with `git commit -m "test: harden CarSky coaching delivery"`.

### Task 29: C3-03 Demo Orchestration and Three-Run Gate

**Owner:** Tư (`four2k3`)  
**Gate / Estimate / Priority:** C3 / 4h / P0  
**Dependencies:** C3-01, C3-02, C3-06, C3-08, C3-09, C3-11, C3-12

**Files:**
- Modify: `src/fleetiq/demo/runner.py`
- Create: `scripts/run_demo_gate.ps1`
- Create: `docs/demo/C3_RUNBOOK.md`

**Produces:** Three consecutive complete runs and recovery instructions.

- [ ] Add stage-level timeout and visible failure status without swallowing exceptions.
- [ ] Run the frozen demo three times from clean process starts.
- [ ] Record run IDs, durations, checksums, receipts, and screenshots.
- [ ] Commit with `git commit -m "test: enforce three-run demo gate"`.

### Task 30: C3-04 Six-Trip Road/Stereo/Horizon Evaluation

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C3 / 8h / P0  
**Dependencies:** C2-09

**Files:**
- Modify: `scripts/roadface/evaluate_roadface_outputs.py`
- Modify: `scripts/evaluate_stereo_depth.py`
- Create: `docs/metrics/ROADFACE_C3.md`

**Produces:** Six-trip KPI table and error buckets.

- [ ] Run detection, object distance, TTC event, stereo coverage/error, horizon residual, and ego-path metrics.
- [ ] Break down by day, night, rain, class, distance range, and valid depth source.
- [ ] Audit the top false positives and false negatives with evidence frames.
- [ ] Commit metrics/config only with `git commit -m "test: evaluate road perception across six trips"`.

### Task 31: C3-05 Stereo Rain/Night Fallback Tuning

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C3 / 6h / P1  
**Dependencies:** C3-04

**Files:**
- Modify: `src/fleetiq/geometry/stereo.py`
- Modify: `src/fleetiq/geometry/object_depth.py`
- Modify: `configs/risk_thresholds.yaml`
- Test: `tests/unit/test_depth_fallback.py`

**Produces:** Confidence-driven source fallback without hiding invalid stereo.

- [ ] Add T03 fixtures for rain/night, glare, low texture, and distant sky.
- [ ] Tune confidence and fallback only against train/validation frames, then evaluate frozen frames.
- [ ] Verify no regression beyond the agreed tolerance on T01/T04.
- [ ] Commit with `git commit -m "fix: harden stereo depth fallback in adverse scenes"`.

### Task 32: C3-06 Frozen Road Evidence Overlay

**Owner:** Phi (`babynghe2003`)  
**Gate / Estimate / Priority:** C3 / 4h / P0  
**Dependencies:** C3-04, C3-05

**Files:**
- Create: `src/fleetiq/visualization/overlay.py`
- Modify: `scripts/roadface/visualize_roadface_outputs.py`
- Test: `tests/integration/test_evidence_overlay.py`

**Produces:** Overlay with track, class, distance source, TTC, horizon, ego path, confidence, and event severity.

- [ ] Write image-level smoke tests for bounds, labels, invalid depth, and deterministic dimensions.
- [ ] Render the frozen C3 clip and verify every displayed number links to an output record.
- [ ] Keep raw images and videos in ignored artifacts.
- [ ] Commit with `git commit -m "feat: render frozen road-risk evidence overlay"`.

### Task 33: C3-07 DMS Six-Trip and Subject-Held-Out Evaluation

**Owner:** Trung (`hoangtrung1801`)  
**Gate / Estimate / Priority:** C3 / 8h / P0  
**Dependencies:** C2-12

**Files:**
- Modify: `scripts/dms/evaluate_dms.py`
- Create: `docs/metrics/DMS_C3.md`
- Test: `tests/integration/test_dms_trip_inference.py`

**Produces:** Six-trip state timelines, subject-held-out metrics, failure categories, and inference time.

- [ ] Verify no subject overlap and report per-state sample count.
- [ ] Run all 3,600 frames and report raw/smoothed macro-F1, confusion matrix, transitions/minute, and unknown rate.
- [ ] Audit low light, eye closure, side head pose, and microsleep examples.
- [ ] Commit with `git commit -m "test: evaluate DMS across subjects and trips"`.

### Task 34: C3-08 DMS Freeze and Integration Regression

**Owner:** Trung (`hoangtrung1801`)  
**Gate / Estimate / Priority:** C3 / 8h / P0  
**Dependencies:** C3-07

**Files:**
- Modify: `configs/dms_baseline.yaml`
- Modify: `src/fleetiq/dms/model.py`
- Create: `tests/integration/test_frozen_dms.py`
- Create: `docs/DMS_MODEL_CARD.md`

**Produces:** Frozen model/config hash, CPU fallback behavior, model card, and deterministic timeline.

- [ ] Test missing weight, wrong hash, CPU inference, corrupt frame, batch boundaries, and confidence rejection.
- [ ] Freeze one model only; remove automatic “latest checkpoint” discovery.
- [ ] Re-run frozen C3 DMS timeline twice and compare hashes.
- [ ] Commit with `git commit -m "release: freeze DMS model and regressions"`.

### Task 35: C3-09 Fusion Threshold Tuning

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C3 / 8h / P0  
**Dependencies:** C2-16, C3-04, C3-07

**Files:**
- Modify: `configs/risk_thresholds.yaml`
- Modify: `src/fleetiq/fusion/rules.py`
- Test: `tests/unit/test_frozen_risk_thresholds.py`

**Produces:** Frozen event-window thresholds and explainable score impacts.

- [ ] Create curated positive/negative windows for TTC, fast corner, distraction, drowsiness, and compound events.
- [ ] Tune on non-demo windows and evaluate the frozen demo window last.
- [ ] Report sensitivity, precision, recall, duplicate rate, and score breakdown stability.
- [ ] Commit with `git commit -m "test: tune and freeze risk thresholds"`.

### Task 36: C3-10 Final KPI Report and Reproduction

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C3 / 6h / P0  
**Dependencies:** C3-04, C3-07, C3-09, C3-02

**Files:**
- Create: `scripts/generate_kpi_report.py`
- Create: `docs/metrics/FINAL_KPI_REPORT.md`
- Test: `tests/integration/test_kpi_report.py`

**Produces:** One command that rebuilds all published tables from metric JSON.

- [ ] Test required KPI names, sample sizes, config/model hashes, and missing metric failure.
- [ ] Generate Road, stereo, TTC, vehicle dynamics, DMS, Fusion, CarSky, and demo reliability sections.
- [ ] Ensure claims distinguish live, simulated, cached, and mock evidence.
- [ ] Commit with `git commit -m "docs: generate reproducible final KPI report"`.

### Task 37: C3-11 Event Regression and Evidence Traceability

**Owner:** Kha (`khaphan11`)  
**Gate / Estimate / Priority:** C3 / 6h / P0  
**Dependencies:** C3-09

**Files:**
- Create: `tests/integration/test_event_traceability.py`
- Create: `docs/metrics/EVENT_AUDIT_C3.md`

**Produces:** Every demo event traces to frame/timestamp, producer signals, threshold, score impact, and evidence.

- [ ] Test orphan evidence, missing source IDs, invalid time ranges, duplicate event IDs, and non-finite values.
- [ ] Audit all emitted events in the frozen demo trip.
- [ ] Fail the demo gate when a displayed event cannot be traced.
- [ ] Commit with `git commit -m "test: enforce risk-event evidence traceability"`.

### Task 38: C3-12 Post-Trip Coaching Report

**Owner:** Dũng (`VKUNeMo`)  
**Gate / Estimate / Priority:** C3 / 6h / P1  
**Dependencies:** C2-18, C3-10

**Files:**
- Create: `src/fleetiq/coaching/report.py`
- Create: `tests/unit/test_coaching_report.py`
- Create: `docs/demo/COACHING_REPORT_SAMPLE.md`

**Produces:** Three evidence-linked coaching actions and one positive recovery observation.

- [ ] Test factual grounding, ranking, dedupe, language, empty trip, and no-recovery cases.
- [ ] Generate the frozen demo report from real RiskEvents only.
- [ ] Verify every claim links to event ID and timestamp.
- [ ] Commit with `git commit -m "feat: generate grounded post-trip coaching report"`.

### Task 39: C3-13 Three-Minute Uncut Video

**Owner:** Dũng (`VKUNeMo`)  
**Gate / Estimate / Priority:** C3 / 6h / P0  
**Dependencies:** C3-03, C3-06, C3-08, C3-10, C3-12

**Files:**
- Create: `docs/demo/C3_VIDEO_SCRIPT.md`
- Create: `docs/demo/C3_VIDEO_SHOTLIST.md`

**Produces:** Exactly one three-minute uncut demo recording plus backup replay.

- [ ] Time the script to 180 seconds with problem, inputs, risk event, DMS, trajectory, CarSky intervention, KPI, and value.
- [ ] Record one continuous take from a clean demo start.
- [ ] Verify audio, text readability, no secret exposure, and matching run ID.
- [ ] Store video outside Git and commit scripts with `git commit -m "docs: finalize uncut C3 demo video plan"`.

### Task 40: C3-14 Final Pitch and Submission QA

**Owner:** Dũng (`VKUNeMo`)  
**Gate / Estimate / Priority:** C3 / 6h / P0  
**Dependencies:** C3-10, C3-13

**Files:**
- Modify: `UchiHahaha-Hackathon2026.pptx`
- Modify: `README.md`
- Create: `docs/SUBMISSION_CHECKLIST.md`

**Produces:** Final pitch, current setup/demo instructions, and submission checklist.

- [ ] Update slides with verified KPIs, CarSky topology, fast-corner/trajectory/stereo/horizon evidence, and limitations.
- [ ] Validate every numeric claim against `FINAL_KPI_REPORT.md`.
- [ ] Check repository URL, team names, video link, proposal file, license notes, and no secret/data artifacts.
- [ ] Run final link/file checks and commit with `git commit -m "docs: finalize hackathon pitch and submission"`.

---

## GitHub Project Creation Plan

Create Project v2: **FleetIQ Guardian - BTC Milestone Execution**.

### Project Fields

| Field | Type | Values |
|---|---|---|
| Status | Single select | Backlog, Ready, In Progress, In Review, Blocked, Done |
| Gate | Single select | C0, C1, C2, C3, Submission |
| Workstream | Single select | Standardization, Road-facing/Depth, Vehicle Dynamics, DMS, Fusion, CarSky/IVI, Demo/QA |
| Priority | Single select | P0, P1, P2 |
| Estimate | Number | Hours from this plan |
| Risk | Single select | Low, Medium, High |
| Assignees | Built-in | GitHub usernames from this plan |

### Milestones

- `C0 - Scope Recovery`: due 2026-07-28
- `C1 - Skeleton Recovery`: due 2026-07-29
- `C2 - Midterm Platform Demo`: due 2026-08-03
- `C3 - Code Freeze`: due 2026-08-08
- `Submission`: due 2026-08-10

### Epics

1. Project Standardization and Demo Skeleton.
2. Road-facing Collision Risk, Stereo Depth, and Horizon.
3. Vehicle Dynamics and Trip Trajectory.
4. Driver Monitoring System.
5. Risk Fusion and Coaching Policy.
6. CarSky IVI and Final Demo.

### Creation Order

1. Create labels, milestones, project fields, and six epic issues.
2. Create Tasks 1-40 without dependency links and record returned issue numbers.
3. Patch each issue body to replace task IDs in `Dependencies` with actual `#issue` links.
4. Add all issues to Project v2 and set Gate, Workstream, Priority, Estimate, Risk, Status, and Assignee.
5. Set C0/C1 recovery tasks to Ready/In Progress according to actual state; leave later tasks Backlog until dependencies close.
6. Verify totals: 40 execution issues, 250 estimated hours, and owner totals `52/58/44/54/42`.

## Plan Verification Commands

```powershell
uv run ruff check .
uv run pytest -q
git diff --check
git status --short
```

Before C3 is marked complete:

```powershell
uv run python scripts\verify_release.py
powershell -ExecutionPolicy Bypass -File scripts\run_demo_gate.ps1
```

Expected result: all CPU tests pass, required opt-in evidence is attached, and three consecutive frozen demo runs complete without a P0/P1 failure.
