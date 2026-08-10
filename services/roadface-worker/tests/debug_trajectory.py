import json, sys
from pathlib import Path
data = json.loads(Path("/artifacts/trips/T01d/trip_data.json").read_text())
traj = data["trajectory"]
points = traj["points"]
print(f"Points: {len(points)}")
p0 = points[0]
print(f"Keys: {sorted(p0.keys())}")
from fleetiq_api.schemas import TrajectoryPoint, TrajectoryData
try:
    tp = TrajectoryPoint(**p0)
    print(f"OK: frame={tp.frame_index} speed={tp.speed_kmh} driver={tp.driver_state}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()