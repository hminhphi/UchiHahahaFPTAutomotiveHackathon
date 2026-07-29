# Road-Facing Training

Offline road-facing workflows are separated from the deployable
`fleetiq-roadface` runtime.

## Commands

```powershell
uv run --package fleetiq-training-roadface fleetiq-label-roadface --help
uv run --package fleetiq-training-roadface fleetiq-prepare-roadface --help
uv run --package fleetiq-training-roadface fleetiq-train-roadface --help
uv run --package fleetiq-training-roadface fleetiq-evaluate-roadface --help
```

Set `FLEETIQ_DATA_ROOT` to the directory that directly contains trip folders,
or pass a command-specific `--dataset-root`. Defaults preserve the existing
repository workflow when commands are run from the repository root.

The LocateAnything and model-training dependencies are loaded only after
arguments are parsed. Asking for `--help` does not initialize Torch, CUDA, or
model weights.

The training package installs GUI-capable `opencv-python` and `imageio` by
default because its annotation, playback, and GIF audit programs are
user-facing. Do not install `opencv-python-headless` into the same environment;
the deployable worker uses its isolated `headless` extra instead.
