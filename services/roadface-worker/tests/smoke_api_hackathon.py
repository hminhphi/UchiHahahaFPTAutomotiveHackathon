"""Smoke test: API discovers Hackathon trips."""
import os
os.environ["FLEETIQ_TESTING"] = "true"
os.environ["FLEETIQ_REPLAY_ENABLED"] = "true"
os.environ["FLEETIQ_MEDIA_BACKEND"] = "filesystem"
os.environ["FLEETIQ_DATASET_ROOT"] = "data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted"

from fleetiq_api.main import create_app
from fastapi.testclient import TestClient

app = create_app(testing=True)
with TestClient(app) as c:
    r = c.get("/api/v1/trips")
    data = r.json()
    trips = data["data"]["items"]
    print(f"Trips found: {len(trips)}")
    for t in trips[:5]:
        sid = t.get("trip_id", "?")
        score = t.get("safety_score", "?")
        sev = t.get("severity", "?")
        ds = t.get("driver_state", "?")
        print(f"  {sid:15s} score={score} severity={sev} driver={ds}")
    if len(trips) > 5:
        print(f"  ... and {len(trips) - 5} more")