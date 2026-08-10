# Final Release Reproduction

## Purpose

This runbook lets an Automotive Hackathon reviewer reproduce the final FleetIQ Guardian dashboard and inspect the exact supporting evidence. The code release, organizer dataset, and generated runtime artifacts are intentionally separate because the dataset and weights are local-only in Git.

## Inputs

1. Source at Git tag `v1.1.2`.
2. `FleetIQGuardian-v1.1.2-runtime.zip`, produced by `tools/release/create_release_package.ps1`.
3. Approved organizer data placed at `data/Practice_Dataset/Practice_Dataset/` and `data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted/`.
4. Docker Desktop, Python 3.12 with uv, Node.js 22, and pnpm 11.

## Restore Runtime Evidence

Extract the source archive, then copy these folders from the runtime archive into the source tree:

```text
runtime/artifacts/   -> artifacts/
runtime/predictions/ -> predictions/
runtime/submission/  -> submission/
```

Verify package integrity before copying:

```powershell
Get-FileHash -Algorithm SHA256 <file>
```

Compare key source, model, and submission files to `MANIFEST.sha256` in the runtime archive. The manifest also records the file count and byte count of the large artifact directories.

## Start The Dashboard

```powershell
uv sync --all-packages --group dev
pnpm install --frozen-lockfile
Copy-Item .env.example .env
docker compose --profile full up --build
```

Open `http://localhost:3000`, then inspect T01d. The expected reviewer path is fleet overview -> T01d -> rule score and event cards -> road replay -> frame-linked evidence.

## Verify Submission Outputs

```powershell
uv run python tools/dataset/validate_submission.py --predictions-dir predictions/UchiHahaha
uv run python data/team-kit/Package_starterkit/package_starterkit/team_kit/evaluation.py --predictions artifacts/evaluation/custom_predictions/UchiHahaha/T01-Sample.csv --trip-dir data/Practice_Dataset/Practice_Dataset/T01-Sample --output artifacts/evaluation/T01-Sample_custom_evaluation.json
```

The evaluator command is for the full-GT Practice trip only. Do not infer redacted-trip ground truth from it.

## Build A Private Handoff Package

```powershell
./tools/release/create_release_package.ps1 -Version v1.1.2 -PrivateReviewerHandoff
```

The default package excludes data. For an organizer-approved private transfer that needs to run without a separate data download:

```powershell
./tools/release/create_release_package.ps1 -Version v1.1.2 -PrivateReviewerHandoff -IncludeDataset
```

Do not attach an `-IncludeDataset` archive to a public release without organizer permission.

The optional YOLOP mask set is large and not required by the primary replay flow. Add it only when a reviewer needs every segmentation overlay:

```powershell
./tools/release/create_release_package.ps1 -Version v1.1.2 -PrivateReviewerHandoff -IncludeYolopMasks
```
