# Services

Purpose: Contains FleetIQ backend services and service-specific integration code.

Owner: Backend Engineering.

Committed/generated policy: Commit service source, configuration, and tests; do not commit build output, caches, or runtime-generated files.

Inputs: Normalized telemetry, camera-derived events, and shared package contracts.

Outputs: APIs, analysis jobs, and dashboard-ready service responses.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
