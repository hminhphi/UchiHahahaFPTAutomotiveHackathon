import json
import traceback
from pathlib import Path

from fleetiq_api.schemas import TrajectoryPoint


data = json.loads(Path("/artifacts/trips/T01d/trip_data.json").read_text())
traj = data["trajectory"]
points = traj["points"]
print(f"Points: {len(points)}")
p0 = points[0]
print(f"Keys: {sorted(p0.keys())}")

try:
    tp = TrajectoryPoint(**p0)
    print(f"OK: frame={tp.frame_index} speed={tp.speed_kmh} driver={tp.driver_state}")
except Exception as error:
    print(f"ERROR: {error}")
    traceback.print_exc()
