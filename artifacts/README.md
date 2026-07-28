# Artifacts

Purpose: Defines the local output mount point for generated FleetIQ artifacts.

Owner: Platform Engineering.

Committed/generated policy: Commit only this boundary README; do not commit renders, reports, model caches, downloaded weights, or generated outputs.

Inputs: Application, service, ML, and research workflow outputs.

Outputs: Local reports, media, caches, and other generated artifacts.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
