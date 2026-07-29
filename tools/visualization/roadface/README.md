# Road-Facing Visualization and Audit

This folder contains human-facing annotation, audit, demo, and visualization
programs. Run them after installing `fleetiq-training-roadface`, whose default
dependencies include GUI-capable OpenCV and `imageio`:

Examples:

```powershell
uv sync --package fleetiq-training-roadface
uv run --package fleetiq-training-roadface python tools/visualization/roadface/annotate_lane_mask.py --help
uv run --package fleetiq-training-roadface python tools/visualization/roadface/visualize_kitti_labels.py --help
uv run --package fleetiq-training-roadface python tools/visualization/roadface/audit_plane_lane.py --help
```

Do not add `opencv-python-headless` to this environment. Both distributions
provide the same `cv2` package, and the headless build cannot open HighGUI
windows.

These programs import `fleetiq_data`, `fleetiq_roadface`, or
`fleetiq_training_roadface`; they do not modify `sys.path` or depend on retired
source namespaces.
