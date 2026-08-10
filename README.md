<!-- prettier-ignore -->
<div align="center">

# FleetIQ Guardian

**Remote driver intelligence and collision-risk evidence platform**

Challenge #3 submission for FPT Automotive Hackathon 2026

[Submission](#submission) | [Release](#release) | [Models](#models-and-runtime) | [Run locally](#reviewer-quick-start) | [Documentation](#documentation)

</div>

## What Reviewers See

FleetIQ Guardian turns multi-view road cameras, in-cabin driver signals, GT depth, and organizer telemetry into a reviewable trip workflow:

```text
Fleet overview -> trip detail -> event timeline -> synchronized evidence -> coaching action
```

The submission targets **Challenge #3: Driver Intelligence Platform**. Challenge #1 transparent scoring and Challenge #2 TTC/near-miss evidence are the product engines underneath it.

![FleetIQ rule-based evidence architecture](docs/architecture/diagrams/12_rule_based_risk_architecture.png)

The diagram source is [12_rule_based_risk_architecture.puml](docs/architecture/diagrams/12_rule_based_risk_architecture.puml). The event and coaching flow is documented in [13_rule_based_event_and_coaching.puml](docs/architecture/diagrams/13_rule_based_event_and_coaching.puml).

## Submission

| Deliverable | Canonical location | Status |
| --- | --- | --- |
| Final report | [docs/Automotive Hackthon - Final Vòng 2.docx.md](docs/Automotive%20Hackthon%20-%20Final%20V%C3%B2ng%202.docx.md) | Filled organizer template; team contact, video URL, and evidence URL must be completed before portal upload |
| Final deck | [PPTX](docs/proposal/UchiHahaha_FleetIQGuardian_Final_Round2.pptx) and [PDF](docs/proposal/UchiHahaha_FleetIQGuardian_Final_Round2.pdf) | One reviewed 14-slide pair |
| Prediction CSVs | `predictions/UchiHahaha/T01d.csv` through `T10d.csv` | Regenerated and validated from final artifacts |
| Evidence and submission runbook | [docs/runbooks/full-evidence-flow.md](docs/runbooks/full-evidence-flow.md) | Rebuilds all ten trips and validates CSVs |
| Upload workspace | `submission/UchiHahaha_FleetIQ_Guardian_Round2_Final/` | Private packet, not a public source-release asset |

### Evidence Boundaries

- Trip safety scores are deterministic `RiskScorer` outputs tied to evidence windows. They are **not** fleet rankings, fleet averages, blind-test accuracy, or organizer evaluation results.
- Road TTC uses GT-depth ROI for retained ego-corridor detections. The fixed image corridor is a filtering heuristic, not a calibrated lane model.
- DMS runtime uses MediaPipe face geometry with 15-frame smoothing. It is not the offline sequence-checkpoint runtime.
- T08d road-left frame 1615 is a source gap and remains explicitly unavailable; the replay never substitutes a nearby frame.

## Reviewer Quick Start

Prerequisites: Python 3.12, uv, Node.js 22, pnpm 11, Docker Desktop, approved organizer data, and the private runtime evidence package when reviewing generated artifacts.

```powershell
uv sync --all-packages --group dev
pnpm install --frozen-lockfile
Copy-Item .env.example .env
docker compose --profile full up -d --build
```

Open <http://localhost:3000/trips/T01d>. The expected path is:

1. Inspect the completed rule score and its component breakdown.
2. Select a consolidated event window from the timeline.
3. Review synchronized road video, DMS state, depth/TTC, and telemetry at the same frame.
4. Inspect the coaching context linked to the event evidence.

Verify the final score artifact directly:

```powershell
curl.exe http://localhost:8000/api/v1/trips/T01d/analysis/fusion/summary
```

For artifact regeneration, replay media, CSV export, and submission validation, follow [full-evidence-flow.md](docs/runbooks/full-evidence-flow.md). For a private reviewer handoff, follow [final-release.md](docs/runbooks/final-release.md).

## Models And Runtime

| Capability | Runtime source | Local artifact location | Release policy |
| --- | --- | --- | --- |
| Road objects | Precomputed `label2_yolo_v3` labels | `artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt` | Weights remain private unless redistribution is approved |
| TTC distance | GT depth ROI on retained detections | `data/.../kitti/depth/` and `artifacts/trips/<trip>/analysis/road/` | Organizer data is never public |
| DMS state | MediaPipe Face Landmarker, geometry rules, 15-frame smoothing | `artifacts/models/dms/face_landmarker.task` | Private runtime dependency |
| Offline DMS checkpoint | Training/evaluation artifact, not the final dashboard runtime | `artifacts/models/dms/best_sequence_model.pt` | Do not use its metric as runtime performance |
| Fusion score and coaching | Deterministic `RiskScorer` and event mapping | `artifacts/trips/<trip>/analysis/fusion/` | Trip evidence only; not a fleet-rank model |

Read [final model provenance](docs/models/PROVENANCE_FINAL.md) before making model or performance claims.

## Release

`v1.1.0` is the final Round 2 source-release candidate.

| Package | Audience | Contents | Command |
| --- | --- | --- | --- |
| GitHub source release | Public reviewers | Source code, committed documentation, final report source, and final deck | Tag and publish `v1.1.0` |
| Runtime evidence handoff | Organizer-approved private reviewers | Models, generated trip artifacts, predictions, report, and submission workspace | `./tools/release/create_release_package.ps1 -Version v1.1.0 -PrivateReviewerHandoff` |
| Portal packet | Automotive Hackathon reviewers | Report, final deck, ten CSVs, selected evidence, and video/link placeholders | `submission/UchiHahaha_FleetIQ_Guardian_Round2_Final_READY_FOR_UPLOAD.zip` |

Do not publish organizer data, model weights, generated trip media, or the private runtime ZIP without explicit organizer approval.

## Repository Map

```text
apps/        Next.js dashboard, FastAPI, and CarSky integration surface
services/    Roadface, DMS, fusion, coaching, and event processing
packages/    Shared contracts, data access, model clients, observability
ml/          Offline training and evaluation code
tools/       Dataset, visualization, presentation, and release automation
docs/        Architecture, models, proposal, submission, demos, and runbooks
artifacts/   Ignored local models and generated evidence
data/        Ignored organizer datasets
```

## Quality Gates

```powershell
uv lock --check
uv run ruff check apps packages services ml infra tools
uv run pytest -q
pnpm --filter @fleetiq/web lint
pnpm --filter @fleetiq/web typecheck
pnpm --filter @fleetiq/web test
pnpm --filter @fleetiq/web build
uv run python tools/dataset/validate_submission.py --predictions-dir predictions/UchiHahaha
docker compose --profile full config
```

## Documentation

| Area | Purpose |
| --- | --- |
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/submission/](docs/submission/README.md) | Final report, checklist, and packet manifest |
| [docs/proposal/](docs/proposal/README.md) | Final judge-facing deck and export |
| [docs/models/](docs/models/PROVENANCE_FINAL.md) | Runtime role, provenance, and disclosure |
| [docs/runbooks/](docs/runbooks/README.md) | Regeneration, validation, and private release handoff |
| [docs/demo/](docs/demo/README.md) | Final demo script and evidence flow |
| [docs/architecture/](docs/architecture/README.md) | System boundaries and rule diagrams |

## Team

UchiHahaha: Phi, Trung, Dung, Kha, and Tu.
