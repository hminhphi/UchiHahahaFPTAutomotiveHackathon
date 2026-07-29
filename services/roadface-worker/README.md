# FleetIQ Roadface Worker

Installable CPU-safe road-facing runtime for frame orchestration, depth,
lane estimation, object tracking, relative speed, and TTC.

The worker consumes explicit FleetIQ dataset records and emits strict
`InferenceResponse` payloads. Dataset roots, output paths, and optional model
clients are supplied by callers; no data, artifacts, or model weights are
packaged with the service.

Run one Practice frame from the repository root:

```powershell
uv run --package fleetiq-roadface --extra headless fleetiq-roadface `
  --dataset practice --trip T01-Sample --start 0 --end 0 --depth-source gt
```

The default output is
`artifacts/predictions/roadface/<trip-id>/<frame-index>.json`. Use
`--dataset-root` and `--output-dir` to inject different locations. Python
callers instantiate `RoadfacePipeline` with `DatasetPaths`, an output root, and
optional detector/depth clients.

`--start` and `--end` select organizer frame IDs, even when frame records are
sparse or out of order. Ground-truth depth lookup is causal and uses only the
latest depth sample at or before each frame.

Validate the package:

```powershell
uv run --package fleetiq-roadface --extra headless pytest services/roadface-worker/tests -v
uv run ruff check services/roadface-worker
```

The `headless` extra is required for worker/model environments and installs
`opencv-python-headless` without GUI libraries. Keep it separate from the
training/tools environment, which intentionally installs `opencv-python`.

The default package remains importable without either OpenCV distribution so
contracts and public data types can be inspected in dependency-light
environments. `RoadfacePipeline` and `PipelineOptions` are loaded lazily; using
them without an OpenCV runtime raises an install instruction instead of
breaking `import fleetiq_roadface` or CLI `--help`.
