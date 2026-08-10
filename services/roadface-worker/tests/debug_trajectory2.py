import asyncio
from pathlib import Path

from fleetiq_api.historical_replay import HistoricalTripRepository
from fleetiq_api.schemas import TrajectoryPoint


async def main() -> None:
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
            try:
                tp = TrajectoryPoint(**p0)
                print(f"OK: frame={tp.frame_index}")
            except Exception as error:
                print(f"TP ERROR: {error}")


asyncio.run(main())
