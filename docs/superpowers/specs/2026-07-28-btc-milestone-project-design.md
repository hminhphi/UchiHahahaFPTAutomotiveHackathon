# FleetIQ Guardian BTC Milestone Project Design

**Date:** 2026-07-28  
**Team:** UchiHahaha  
**Final submission date:** 2026-08-10  
**Code freeze:** 2026-08-08  
**Repository:** `babynghe2003/UchiHahahaFPTAutomotiveHackathon`

## 1. Objective

Deliver one reliable FleetIQ Guardian vertical slice that converts synchronized road camera, driver camera, depth, calibration, and telemetry inputs into:

1. Road-facing collision-risk signals.
2. Driver monitoring states.
3. Time-aligned compound-risk events.
4. Safety-gated coaching commands.
5. A visible coaching intervention on the CarSky Android Automotive device.
6. Timestamped evidence, initial KPIs, and a repeatable three-minute demo.

The plan follows the organizer's C0-C3 delivery gates. Work is not divided into equal research weeks; every task must contribute to the next gate.

## 2. Scope

### Must Have

- One Practice Dataset trip runs end-to-end through Road-facing, DMS, Fusion, Safety Gate, and CarSky IVI Coaching.
- Road-facing output contains tracked obstacle, distance, relative speed, TTC, confidence, and evidence frame.
- DMS output uses the normalized states `attentive`, `distracted`, `drowsy`, and `unknown`.
- Fusion produces canonical risk events with severity, confidence, explanation, and source references.
- Safety Gate suppresses low-confidence, stale, duplicate, or distracting interventions.
- CarSky receives a coaching command through a documented adapter and renders it in the Android Automotive guest.
- The team reports initial Road-facing, DMS, Fusion, and platform-delivery KPIs.
- A clean environment can run automated tests and replay the frozen demo.

### Nice to Have

- Voice or haptic coaching.
- Personalized LLM-generated post-trip coaching.
- Advanced curved-lane reconstruction beyond what is needed to select ego-path obstacles.
- Full fleet dashboard and batch analytics across every trip.
- Real-time optimization of large transformer models.

Nice-to-have issues remain outside the critical path and may only start after the C2 acceptance criteria pass.

### Out of Scope

- A full autonomous-driving stack.
- Safety-critical vehicle actuation.
- Automatic braking or steering commands.
- Commercial deployment or homologation.
- Training every perception model from scratch.

## 3. Organizer Gates

| Gate | Internal due date | Required evidence | Acceptance criteria |
|---|---|---|---|
| **C0 Recovery** | 2026-07-28 | One-page scope and risk register | Must-have, nice-to-have, stack, GPU/API/CarSky needs, and top risks are committed to the repository. |
| **C1 Recovery** | 2026-07-29 | Five-minute skeleton demo and one-page progress report | One trip traverses every interface. Road-facing may use current outputs, DMS may use a deterministic stub, and CarSky may use a mock adapter. Every stub is visibly marked. |
| **C2 Midterm** | 2026-08-03 | Ten-minute live/video demo on the platform and initial KPI report | Road-facing and DMS use real inference outputs; Fusion generates at least one compound event; one coaching command reaches CarSky; initial KPI values are reproducible. |
| **C3 Code Freeze** | 2026-08-08 | Clean test run, three-minute uncut demo video, and pitch slides | Demo succeeds three consecutive times from frozen inputs. Required tests pass. No critical issue remains open. |
| **Submission** | 2026-08-10 | Final package | Only submission metadata, video, documentation, and pitch corrections are allowed after code freeze. |

## 4. Capacity and Ownership

The team works four to six hours per person per day. Planning uses a conservative committed capacity and preserves contingency for GPU, model, CarSky, and integration failures.

| Owner | GitHub | Primary responsibility | C1 | C2 | C3 | Total |
|---|---|---|---:|---:|---:|---:|
| Tư | `four2k3` | Integration runner, event API, CarSky Blueprint/REST/AAOS bridge | 10h | 22h | 16h | 48h |
| Phi | `babynghe2003` | Road-facing, distance/TTC, ego-path filtering, vehicle signals | 10h | 20h | 16h | 46h |
| Trung | `hoangtrung1801` | DMS inference, state normalization, smoothing, confidence | 8h | 20h | 16h | 44h |
| Kha | `khaphan11` | Time alignment, multimodal fusion, scoring, KPI evaluation | 8h | 20h | 18h | 46h |
| Dũng | `VKUNeMo` | Coaching policy/NLP, IVI content, demo narrative | 6h | 18h | 18h | 42h |

Total committed implementation effort is 226 hours before code freeze. Remaining capacity is reserved for integration and recovery rather than pre-assigned feature work.

## 5. System Design

### 5.1 Data Flow

```text
Practice Dataset
  -> Road-facing inference --------\
  -> DMS inference -----------------+-> Time Alignment
  -> Telemetry normalization -------/       |
                                             v
                                     Compound Risk Engine
                                             |
                                             v
                                         Safety Gate
                                      /                  \
                              suppress/log          CoachingCommand
                                                         |
                                                         v
                                                CarSky Adapter
                                                         |
                                                         v
                                      Android Automotive IVI Coaching
```

### 5.2 Stable Contracts

All modules communicate through versioned JSON-serializable records. Missing values use `null` plus a reason; modules must not invent confidence or measurements.

`FrameContext`:

- `schema_version`
- `trip_id`
- `frame_index`
- `timestamp_ms`
- `ego_speed_mps`
- `source_paths`

`RoadRiskSignal`:

- `track_id`
- `object_class`
- `bbox_xyxy`
- `distance_m`
- `relative_speed_mps`
- `ttc_s`
- `in_ego_path`
- `confidence`
- `evidence_path`

`DriverStateSignal`:

- `state`: `attentive`, `distracted`, `drowsy`, or `unknown`
- `confidence`
- `eye_closure`
- `head_pose`
- `phone_use`
- `evidence_path`

`RiskEvent`:

- `event_id`
- `trip_id`
- `start_ts_ms`
- `end_ts_ms`
- `event_type`
- `severity`: integer from 1 to 5
- `confidence`: float from 0 to 1
- `sources`
- `explanation`
- `evidence`

`CoachingCommand`:

- `command_id`
- `event_id`
- `created_ts_ms`
- `channel`: `visual`, `voice`, or `post_trip`
- `priority`
- `title`
- `message`
- `expires_at_ms`
- `dedupe_key`

### 5.3 Safety Gate

The Safety Gate is deterministic and testable. A real-time coaching command is sent only when:

- Event confidence meets the configured threshold.
- Event age is below the configured latency budget.
- The same `dedupe_key` has not been sent inside the cooldown window.
- Severity and vehicle context justify an in-car interruption.
- A non-distracting message template exists.

Events that fail the gate are retained for dashboard or post-trip coaching. No module sends vehicle-control commands.

### 5.4 CarSky Integration

CarSky follows the platform model documented in `docs/Car-Sky-Platform.html`:

```text
Blueprint -> Deploy -> Room -> Device -> Widget
```

The C2 topology contains:

- A **Container Node** running the FleetIQ coaching adapter.
- A **KUKSA Broker/VSS or REST path** carrying risk/coaching signals.
- A **Skycraft Node** running the Android Automotive guest.
- A Screen widget for live demo and recording.

The adapter interface has two implementations:

- `MockCarSkyAdapter` for C1 and local automated tests.
- `CarSkyAdapter` for the deployed C2/C3 room.

The real adapter must not embed API keys in source control. Missing credentials or unavailable rooms cause a logged, visible fallback to mock/replay mode.

## 6. KPI Design

Initial C2 KPIs use a frozen, manually audited sample so results are reproducible.

| Area | KPI | C2 reporting rule |
|---|---|---|
| Road-facing | Detection precision/recall and distance MAE | Report by obstacle class on the audited sample; compare distance against organizer depth/ground truth where available. |
| Collision risk | TTC event precision/recall | Evaluate threshold crossings on labeled event windows, not isolated frames. |
| DMS | Macro-F1 and state transition rate | Report four-state macro-F1 plus transitions per minute to expose flicker. |
| Fusion | Compound-event precision | Manually review every emitted compound event in the frozen demo trip. |
| CarSky | Delivery success rate and p95 latency | Replay at least 20 commands; target at least 95% delivery and p95 event-to-display latency at or below 1,000 ms. |
| Demo | Consecutive successful runs | C3 requires three successful end-to-end runs from a clean process start. |

KPI reports include sample size, trip/frame selection, model/config version, and known limitations.

## 7. Project Standardization

Standardization is a delivery enabler, not a repository-wide rewrite. Existing Road-facing experiments remain in `scripts/roadface`; stable cross-workstream code moves into a small installable package.

### 7.1 Target Layout

```text
src/fleetiq/
  common/             configuration, logging, paths, run metadata
  contracts/          FrameContext and versioned signal/event schemas
  dms/                normalized DMS adapter interface
  roadface/           normalized Road-facing adapter interface
  fusion/             alignment, risk rules, scoring, safety gate
  carsky/             mock and real CarSky adapters
  demo/               end-to-end orchestration and replay CLI
configs/
  demo.yaml
  risk_thresholds.yaml
  coaching_templates.yaml
tests/
  unit/
  contract/
  integration/
.github/
  workflows/ci.yml
  ISSUE_TEMPLATE/
  pull_request_template.md
  CODEOWNERS
```

### 7.2 Standard Commands

```powershell
uv sync --extra dev
uv run ruff check .
uv run pytest -q
uv run python -m fleetiq.demo --trip T06-Sample --adapter mock
uv run python -m fleetiq.demo --trip T06-Sample --adapter carsky
```

The first three commands must be CPU-safe. GPU tests are opt-in and cannot block pull-request CI.

### 7.3 Configuration and Secrets

- Python version remains `>=3.12,<3.13`.
- `uv.lock` is the dependency lock file.
- Runtime thresholds live in versioned YAML, not hard-coded across scripts.
- Local dataset/model/cache paths come from config or environment variables.
- `.env.example` documents required variables without containing credentials.
- `data/`, `artifacts/`, model weights, videos, and secrets remain outside Git.
- Every run writes `run_metadata.json` containing commit SHA, config hash, model identifiers, trip, frame range, and start time.

### 7.4 Engineering Workflow

- One GitHub issue maps to one reviewable deliverable and is estimated at two to eight hours.
- Branch names use `feature/<issue>-<short-name>` or `fix/<issue>-<short-name>`.
- Pull requests link their issue and contain test evidence.
- Interfaces and acceptance tests land before model-specific adapters depend on them.
- Generated artifacts are linked from issues but are not committed.
- No direct push to `main` after C2 unless it fixes a P0/P1 issue reviewed by another member.

### 7.5 Definition of Done

An issue is done only when:

- Acceptance criteria in the issue body pass.
- Pure rules have unit tests, schemas have contract tests, external adapters have mock-backed integration tests, and the critical path has a replay test.
- Logs include trip, frame/timestamp, module, and run identifier.
- Configuration and expected outputs are documented.
- The pull request is reviewed by at least one owner of a downstream dependency.
- No dataset, credential, model weight, or generated artifact is committed.

### 7.6 Standardization by Gate

| Gate | Standardization deliverable |
|---|---|
| C1 | Contract v0, one demo entry point, mock adapters, config loader, run/output convention, quick-start command. |
| C2 | Installable package, contract tests, CPU CI, `.env.example`, issue/PR templates, CODEOWNERS, reproducible KPI command. |
| C3 | Frozen config/model manifest, release tag candidate, clean-environment verification, demo replay package, final operating guide. |

## 8. GitHub Project Design

Create Project v2 named **FleetIQ Guardian - BTC Milestone Execution** and link it to the repository.

### Fields

- `Status`: Backlog, Ready, In Progress, In Review, Blocked, Done
- `Gate`: C0, C1, C2, C3, Submission
- `Workstream`: Standardization, Road-facing, DMS, Fusion, CarSky/IVI, Demo/QA
- `Priority`: P0, P1, P2
- `Estimate`: numeric hours
- `Risk`: Low, Medium, High
- `Assignees`: GitHub's built-in assignee field

### Labels

`epic`, `standardization`, `roadface`, `dms`, `fusion`, `carsky`, `ivi`, `backend`, `demo`, `test`, `blocked`, `P0`, `P1`, `P2`

### Issue Rules

Every issue body contains:

- Objective.
- Deliverable.
- Acceptance criteria.
- Estimate.
- Owner.
- Gate.
- `Blocked by` links.
- `Blocks` links.
- Validation command or evidence.

Five epics organize the execution issues:

1. Project Standardization and Demo Skeleton.
2. Road-facing Collision Risk.
3. Driver Monitoring System.
4. Risk Fusion and Coaching Policy.
5. CarSky IVI and Final Demo.

## 9. Dependency Strategy

The critical path is:

```text
Contract and config
  -> normalized Road-facing and DMS outputs
  -> time alignment
  -> compound-risk engine
  -> safety gate and coaching policy
  -> CarSky adapter
  -> Android IVI
  -> end-to-end tests and demo video
```

CarSky access, Blueprint creation, DMS model research, and Road-facing KPI sample preparation begin in parallel. A blocked research task must provide a fallback adapter or frozen output within the same gate.

## 10. Risks and Fallbacks

| Risk | Trigger | Fallback |
|---|---|---|
| CarSky credentials or room unavailable | No working room by 2026-07-31 | Use `MockCarSkyAdapter` for pipeline validation and record the real CarSky integration separately as soon as access returns. |
| DMS model misses C2 | No stable four-state output by 2026-08-01 | Use the best pretrained baseline plus `unknown`; do not fabricate states. |
| Lane/ego-path remains unstable | Curved or occluded samples select wrong obstacles | Use road-plane prior, depth, temporal track continuity, and a frozen validated demo sequence. |
| GPU/model failure | Inference cannot complete within the gate | Use cached, versioned inference outputs and retain live replay for orchestration. |
| Integration drift | Producers emit incompatible fields | Contract tests block merge; adapters translate legacy output into the canonical schema. |
| Scope expansion | Nice-to-have work starts before C2 passes | Move the issue back to Backlog and protect the critical path. |

## 11. Success Criteria

The design succeeds when:

- C1 demonstrates the entire interface chain, with stubs clearly identified.
- C2 demonstrates real Road-facing and DMS outputs, at least one compound event, and one CarSky coaching intervention with initial KPIs.
- C3 passes automated checks and three consecutive demo runs before the 2026-08-08 freeze.
- Every active issue has one owner, estimate, gate, acceptance criteria, and explicit dependencies.
- A new team member can set up, test, and replay the project using documented standard commands.
