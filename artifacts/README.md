# Artifacts

Purpose: Defines the local output mount point for generated FleetIQ artifacts.

Owner: Platform Engineering.

Committed/generated policy: Commit only this boundary README; do not commit renders, reports, model caches, downloaded weights, or generated outputs.

Inputs: Application, service, ML, and research workflow outputs.

Outputs:

- `models/`: downloaded weights, caches, checkpoints, and packaged models.
- `training/`: prepared datasets, training plans, and experiment runs.
- `predictions/`: frame/trip inference outputs.
- `renders/`: generated images, videos, and visual audits.
- `reports/`: generated metrics, evaluations, and summaries.
- `presentations/`: generated slide assets and local backups.
- `research-extracts/`: rendered paper pages, OCR, and extraction outputs.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
