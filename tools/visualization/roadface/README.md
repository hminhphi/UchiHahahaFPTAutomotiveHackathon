# Road-Facing Visualization and Audit

This folder contains human-facing annotation, audit, demo, and visualization
programs. Run them from the repository root after `uv sync --all-packages`.

Examples:

```powershell
uv run --package fleetiq-training-roadface python tools/visualization/roadface/annotate_lane_mask.py --help
uv run --package fleetiq-training-roadface python tools/visualization/roadface/visualize_kitti_labels.py --help
uv run --package fleetiq-training-roadface python tools/visualization/roadface/audit_plane_lane.py --help
```

These programs import `fleetiq_data`, `fleetiq_roadface`, or
`fleetiq_training_roadface`; they do not modify `sys.path` or depend on retired
source namespaces.
