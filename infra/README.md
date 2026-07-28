# Infrastructure

Purpose: Contains infrastructure definitions and deployment automation for FleetIQ.

Owner: Platform Engineering.

Committed/generated policy: Commit declarative infrastructure source and validation scripts; do not commit credentials, local state, generated images, or runtime logs.

Inputs: Service deployment requirements and environment configuration contracts.

Outputs: Reproducible infrastructure and deployment definitions.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
