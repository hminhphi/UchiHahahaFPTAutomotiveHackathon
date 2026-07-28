# Data

Purpose: Defines the local mount point for organizer datasets and approved data inputs.

Owner: Data and Perception Engineering.

Committed/generated policy: Commit only this boundary README; do not commit organizer datasets, extracted data, labels, or local derivatives.

Inputs: Organizer-provided datasets and approved local data sources.

Outputs: Local data paths consumed by training, analysis, and evaluation workflows.

Validation: `uv run pytest tests/architecture/test_repository_skeleton.py -v`
