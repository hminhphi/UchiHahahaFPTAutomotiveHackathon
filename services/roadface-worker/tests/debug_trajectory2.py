import asyncio, json
from pathlib import Path
from fleetiq_api.historical_replay import HistoricalTripRepository

async def main():
    repo = HistoricalTripRepository(None, artifacts_root=Path("/artifacts/trips"))
    data = repo._load_generated("T01d")
    print(f"Loaded: {data is not None}")
    if data:
        traj = data.get("trajectory", {})
        pts = traj.get("points", [])
        print(f"Points: {len(pts)}")
        if pts:
            p0 = pts[0]
            print(f"active_event_types type: {type(p0.get('active_event_types'))}")
            print(f"events type: {type(p0.get('events'))}")
            from fleetiq_api.schemas import TrajectoryPoint, TrajectoryData
            try:
                tp = TrajectoryPoint(**p0)
                print(f"OK: frame={tp.frame_index}")
            except Exception as e:
                print(f"TP ERROR: {e}")
asyncio.run(main())