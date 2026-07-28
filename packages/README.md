# Packages

Purpose: Contains reusable FleetIQ libraries and cross-application contracts.

Owner: Platform Engineering.

Committed/generated policy: Commit package source, manifests, and tests; do not commit built distributions, caches, or generated runtime files.

Inputs: Shared domain models, utilities, and typed interfaces.

Outputs: Versioned libraries consumed by applications, services, and ML tooling.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
