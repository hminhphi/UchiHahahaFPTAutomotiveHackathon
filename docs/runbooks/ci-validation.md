# CI Validation

## Purpose

Run the same CPU-safe checks locally and in GitHub Actions before merging a
shared FleetIQ change. These checks do not require AWS credentials, a GPU, the
organizer dataset, Android Studio, or a live CarSky Room.

## Windows Developer Machine

```powershell
uv sync --all-packages --group dev
uv lock --check
uv run ruff check apps packages services ml infra tools
uv run pytest -q
pnpm install --frozen-lockfile
pnpm --filter @fleetiq/web lint
pnpm --filter @fleetiq/web test
pnpm --filter @fleetiq/web build
docker compose --profile full config
```

Run the integration proof separately after Docker Desktop and the Practice
Dataset are available:

```powershell
docker compose --profile full up --build
uv run --group dev python infra/compose/smoke_test.py
```

The smoke test must report `8/8`. It verifies API readiness, MQTT event flow,
model-mock inference, producer camera ingress, ordered MinIO replay, trip
trajectory telemetry, and CarSky mock acknowledgement.

## Linux CI Requirements

The training and visualization tools intentionally use the GUI-capable
`opencv-python` wheel for local annotation. Linux CI needs runtime libraries
before importing that wheel:

```bash
sudo apt-get update
sudo apt-get install --yes libgl1 libglib2.0-0 libxcb1 libxext6 libxrender1
```

The GitHub workflow installs these libraries before `uv sync`. The deployable
road-facing worker remains separate and uses its `headless` extra, so ECS
runtime images do not depend on GUI libraries.

## Expected Evidence

- Python workspace tests: `234 passed` or greater.
- Ruff: `All checks passed!`.
- Web: lint, unit tests, and production build pass.
- Compose smoke: `8/8`.

If a local `.venv` only contains one package, run `uv sync --all-packages
--group dev` before treating an import failure as an application defect.
