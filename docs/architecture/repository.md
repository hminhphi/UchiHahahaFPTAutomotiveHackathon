# Repository Architecture

FleetIQ is a breaking monorepo refactor. Legacy `scripts/` and root notebooks
are intentionally removed; stable commands belong to installable packages or
named tools.

## Boundaries

| Directory | Responsibility | Committed content |
| --- | --- | --- |
| `apps/` | Next.js dashboard, FastAPI control plane, CarSky Android HMI | Source, tests, Dockerfiles |
| `services/` | MQTT gateway and road/DMS/fusion/coaching workers | Source, tests, Dockerfiles |
| `packages/` | Contracts, dataset kit, model clients, observability | Reusable source and schemas |
| `ml/` | Training, evaluation, SageMaker handlers, notebooks, configs | Code and lightweight configs |
| `tools/` | Dataset, visualization, and presentation entrypoints | Maintained utilities |
| `infra/` | Local Compose, Docker templates, and AWS CDK | Declarative infrastructure |
| `docs/` | Architecture, protocols, proposal, references, reports, runbooks | Approved documentation |
| `research/` | Authored research notes plus ignored raw references/clones | Notes; raw inputs ignored |
| `data/` | Organizer dataset mount | Boundary README only |
| `artifacts/` | Generated outputs and downloaded model files | Boundary README only |

## Dependency Direction

Applications and services may depend on shared packages. Shared packages do not
import applications, services, local datasets, or artifact directories.
Training code can depend on `packages/data-kit` and model contracts but runtime
services must not import experimental notebooks.

All cross-process payloads use `packages/contracts`; importing another
service's internal module is not a substitute for a protocol.

## Local-Only Classification

```text
data/                         Organizer datasets
artifacts/models/             Weights, caches, packaged models
artifacts/training/           Training runs and prepared datasets
artifacts/predictions/        Model and pipeline outputs
artifacts/renders/            Images and videos
artifacts/reports/            Generated metrics and summaries
artifacts/presentations/      Generated slide assets and backups
artifacts/research-extracts/  Extracted paper pages and OCR
research/papers/raw/          Downloaded papers
research/third-party/         Cloned external repositories
```

The architecture test enforces top-level boundaries, ignored local roots, and
the absence of legacy Python imports.
