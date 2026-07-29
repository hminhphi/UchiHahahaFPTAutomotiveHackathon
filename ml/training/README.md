# Model Training

This directory owns offline dataset preparation, relabeling, training, and
evaluation. Training packages may depend on shared data/runtime libraries, but
applications and services must never import training code.

Use the repository-level `uv.lock` and run package commands from the repository
root. Model weights, generated datasets, runs, and predictions belong under
`artifacts/` and are not committed.
