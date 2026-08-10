# ML

Offline training and evaluation code for FleetIQ Guardian. Deployable services
consume generated artifacts; they must not import training modules.

| Area | Location | Final role |
| --- | --- | --- |
| Road-facing detector training | `training/roadface/` | Produces the custom YOLO label/model artifacts used by road evidence generation |
| DMS feature and sequence training | `training/dms/` | Produces offline training/evaluation artifacts; the final dashboard runtime uses MediaPipe geometry rules |
| SageMaker packaging | `sagemaker/` | Deployment packaging experiments, not the local final replay path |
| Notebooks | `notebooks/` | Exploratory and evaluation support only |

Model weights, datasets, generated labels, and predictions belong in ignored
`artifacts/` or `data/` directories. Do not add them to a public source release.

Read [final model provenance](../docs/models/PROVENANCE_FINAL.md) before reporting a
metric or distributing an artifact.

Validation: `uv run pytest -q` and the package-specific commands in each training README.
