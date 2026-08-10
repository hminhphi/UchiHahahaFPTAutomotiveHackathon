# Full Evidence, Event, Risk, And Submission Flow

This runbook regenerates the complete FleetIQ evidence flow for every scored
redacted trip. No command accepts a trip, frame-range, stride, or frame-count
limit: the scripts discover all `T01d` through `T10d` and process every frame
in each trip document.

## Prerequisites

- Python 3.12 and `uv`.
- Organizer redacted dataset at
  `data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted`.
- Existing full `label2_yolo_v3` labels. Refresh these only when the detector
  checkpoint changes; label export itself also runs every source image.
- FFmpeg for full road-left MP4 packaging.
- Docker Desktop for API/web replay verification.

Install dependencies once:

```powershell
uv sync --all-packages --group dev
pnpm install --frozen-lockfile
```

## Full Regeneration

Run each command from the repository root in this order:

```powershell
# Optional only when replacing the detector checkpoint. Processes all road images.
uv run python tools/dataset/export_yolo_labels.py --dataset redacted --overwrite

# Rebuild all DMS-derived trip trajectories and telemetry context.
uv run python services/roadface-worker/tests/generate_trip_data.py

# Rebuild aggregate telemetry fields used by the historical trip documents.
uv run python services/roadface-worker/tests/enrich_detached_trips.py

# Generate 1,800 road, DMS, and fusion frames for every trip.
uv run python services/roadface-worker/tests/generate_ai_artifacts.py `
  --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted `
  --output-dir artifacts/trips `
  --label-dir-name label2_yolo_v3

# Generate full road-left MP4 replay and one complete frame map for every trip.
uv run python tools/media/package_full_road_replay.py `
  --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted `
  --artifacts-root artifacts/trips

# Export and validate all organizer-format prediction CSVs.
uv run python tools/dataset/export_submission.py --team UchiHahaha
uv run python tools/dataset/validate_submission.py `
  --predictions-dir predictions/UchiHahaha `
  --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted
```

## Rule-Based Risk Contract

- Ignore an object when its bounding box is `<=30 px` wide or high.
- Ignore an object unless at least 50% of its box overlaps the fixed
  ego-lane image corridor (`x=250..390` in the 640-pixel road frame). This is
  a filtering heuristic, not a calibrated lane model.
- Estimate road distance from the depth ROI and calculate TTC only for retained
  ego-lane objects.
- `RiskScorer` applies bounded collision, attention, handling, and lane
  penalties. Frame risk is the penalty sum; trip risk is mean frame risk;
  the internal safety value is `100 - trip risk`.
- Fusion writes per-frame `event_codes`, consolidates them into
  `analysis/fusion/events.json`, and maps them to event-specific coaching labels.

The formulas and model/source boundaries are documented in:

- [`12_rule_based_risk_architecture.puml`](../architecture/diagrams/12_rule_based_risk_architecture.puml)
- [`13_rule_based_event_and_coaching.puml`](../architecture/diagrams/13_rule_based_event_and_coaching.puml)
- [`services/fusion-worker/src/fleetiq_fusion/scoring.py`](../../services/fusion-worker/src/fleetiq_fusion/scoring.py)

## Replay And API Validation

The Compose API uses the bind-mounted filesystem dataset, not a partial MinIO
copy, so camera followers serve the source frame IDs directly.

```powershell
docker compose --profile full up -d --build

# Rule-based event windows are navigable from the API.
curl.exe http://localhost:8000/api/v1/trips/T01d/events

# The fusion summary exposes risk score, rule version, and event counts.
curl.exe http://localhost:8000/api/v1/trips/T01d/analysis/fusion/summary

# Full road replay and the final source frame are available.
curl.exe -I http://localhost:3000/api/trips/T01d/road-video/content
curl.exe -I http://localhost:3000/api/trips/T01d/frames/road_right/1799
```

Every trip has 1,800 logical timeline frames. T08d has one organizer source
road-left image gap at frame `1615`; the replay packager inserts an explicit
"SOURCE FRAME UNAVAILABLE" marker at that timestamp rather than silently
substituting a neighboring evidence frame. The individual-frame endpoint still
returns `404` for that missing source image, which is the correct evidence-safe
behavior.

## Scoring Disclosure

The risk artifacts are deterministic and reproducible, but redacted-trip
ground truth is unavailable. Do not present their internal trip safety values
as blind-test accuracy or use them for fleet ranking until the scoring policy is
validated against organizer-approved ground truth.
