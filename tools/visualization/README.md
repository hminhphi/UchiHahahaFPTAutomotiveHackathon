# Visualization Tools

Interactive and offline viewers live here. They consume installed FleetIQ
packages and committed metadata, while rendered images and videos go to `artifacts/`.

- `trip_player.py`: Renders synchronized trip camera, depth, labels, calibration, and telemetry views.
- `visualize_landmarks.py`: Real-time OpenCV GUI explorer for 468 MediaPipe Facial Landmarks, 3D Head Pose (solvePnP), EAR, MAR, and side-by-side comparison between Ground Truth and Solution 2 Bi-LSTM predicted driver state.
- `roadface/`: Road-facing annotation and audit tools.

## Running Landmark Visualizer

```powershell
uv run --package fleetiq-training-dms python tools/visualization/visualize_landmarks.py
uv run --package fleetiq-training-dms python tools/visualization/visualize_landmarks.py --trip T01-Sample
```

### Key Controls:
- **SPACE**: Play / Pause
- **A / D** (or Left/Right Arrows): Previous / Next frame
- **W / S** (or Up/Down Arrows): Speed FPS +/-
- **N / P**: Next / Previous trip
- **ESC / Q**: Exit
