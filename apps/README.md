# Apps

Purpose: Contains deployable FleetIQ user-facing applications.

Owner: Frontend Engineering.

Committed/generated policy: Commit application source, configuration, and tests; do not commit build output, local dependencies, or runtime-generated files.

Inputs: Shared packages and service APIs.

Outputs: Runnable web and human-machine interface applications.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
