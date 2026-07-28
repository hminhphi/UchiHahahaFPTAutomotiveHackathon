# Tools

Purpose: Contains developer tooling used to maintain and validate FleetIQ.

Owner: Platform Engineering.

Committed/generated policy: Commit scripts, tool configuration, and tests; do not commit tool caches, downloaded binaries, or generated local output.

Inputs: Repository source, configuration, and developer commands.

Outputs: Repeatable validation, generation, and maintenance workflows.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
