# FleetIQ Data Kit

`fleetiq_data` is the stable, CPU-only boundary for organizer Practice/KITTI
trip data. It discovers trip folders, loads their gzip documents, parses
calibration and KITTI labels, locates camera/depth frames, and normalizes
telemetry without changing the organizer-owned dataset layout.

Pass a dataset root explicitly to every loader. `DatasetPaths.from_env()` is
the only convenience entry point that reads `FLEETIQ_DATA_ROOT`.

```powershell
uv run --package fleetiq-data-kit python -m fleetiq_data.trips --root data/Practice_Dataset/Practice_Dataset
```
