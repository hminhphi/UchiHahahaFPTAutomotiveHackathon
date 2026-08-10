"""Generate all trip data for dashboard from Hackathon detached dataset using YOLOv26 + DMS pseudo-labels."""

from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fleetiq_api.trajectory import build_trajectory
from fleetiq_training_dms.feature_extractor import extract_features_from_trip
from fleetiq_training_dms.pseudo_labels import apply_geometry_pseudo_labels, STATE_MAP

STATE_INV = {v: k for k, v in STATE_MAP.items()}

HACKATHON_ROOT = Path("data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted")
OUTPUT_ROOT = Path("artifacts/trips")


def main() -> None:
    os.environ.setdefault("FLEETIQ_DATA_ROOT", str(HACKATHON_ROOT))

    if not HACKATHON_ROOT.is_dir():
        print(f"Dataset not found: {HACKATHON_ROOT}", file=sys.stderr)
        sys.exit(1)

    trip_ids = sorted(
        d.name for d in HACKATHON_ROOT.iterdir()
        if d.is_dir() and d.name.startswith("T") and d.name.endswith("d")
    )
    print(f"Found {len(trip_ids)} detached trips: {trip_ids}")

    all_trips = []
    for trip_id in trip_ids:
        print(f"\n{'='*60}")
        print(f"Trip: {trip_id}")

        trip_dir = HACKATHON_ROOT / trip_id
        json_path = trip_dir / f"{trip_id}.json.gz"
        if not json_path.is_file():
            print("  SKIP: no JSON.gz found")
            continue

        data = json.loads(gzip.decompress(json_path.read_bytes()))
        frames = data.get("frames", [])
        print(f"  Frames: {len(frames)}")

        # Geometry comes from the API's canonical builder so the dashboard and
        # the API never disagree. For detached trips it dead-reckons position
        # from speed and lateral acceleration, because ego.location is redacted.
        built = build_trajectory(trip_id, data)
        trajectory = [
            {
                "frame_index": point.frame_index,
                "timestamp_s": point.timestamp_s,
                "x_m": round(point.x_m, 2),
                "y_m": round(point.y_m, 2),
                "speed_kmh": round(point.speed_kmh, 1),
                "longitudinal_accel_mps2": round(point.longitudinal_accel_mps2, 2),
                "lateral_accel_mps2": round(point.lateral_accel_mps2, 2),
                "min_ttc_s": point.min_ttc_s,
                "headway_s": point.headway_s,
                "driver_state": point.driver_state,
                "driver_alertness": point.driver_alertness,
                "simulator_risk_score": point.simulator_risk_score,
                "active_event_types": list(point.active_event_types),
                "events": list(point.events),
            }
            for point in built.points
        ]

        # DMS driver state extraction
        try:
            df_feat = extract_features_from_trip(trip_dir, is_train=False)
            df_labeled = apply_geometry_pseudo_labels(df_feat)
            for i, row in df_labeled.iterrows():
                frame_id = int(row.get("frame_id", 0))
                if frame_id < len(trajectory):
                    state = STATE_INV.get(int(row.get("state_label", -1)), "unknown")
                    # Normalize to 4 standard states
                    if state in {"microsleep", "yawning"}:
                        state = "drowsy"
                    elif state == "alert":
                        state = "attentive"
                    trajectory[frame_id]["driver_state"] = state
                    trajectory[frame_id]["driver_alertness"] = round(float(row.get("ear", 0.25)), 3)
                    if np.isnan(trajectory[frame_id]["driver_alertness"]):
                        trajectory[frame_id]["driver_alertness"] = None
            print(f"  DMS: {len(df_labeled)} driver states generated")
        except Exception as e:
            print(f"  DMS warning: {e}")

        # Compute trip summary
        max_speed = built.max_speed_kmh

        trip_data = {
            "trip_id": trip_id,
            "status": "complete",
            "driver_state": "unknown",
            "max_speed_kmh": round(max_speed, 1),
            "trajectory": {
                "trip_id": trip_id,
                "points": trajectory,
                "distance_m": built.distance_m,
                "max_speed_kmh": built.max_speed_kmh,
                "max_lateral_accel_mps2": built.max_lateral_accel_mps2,
            },
        }
        all_trips.append(trip_data)

        # Save per-trip JSON
        out_dir = OUTPUT_ROOT / trip_id
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "trip_data.json").write_text(json.dumps(trip_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved: {out_dir / 'trip_data.json'}")

    # Save fleet summary
    fleet_summary = {
        "trips": all_trips,
        "total": len(all_trips),
        "generated_at": str(pd.Timestamp.now()),
    }
    (OUTPUT_ROOT / "fleet_summary.json").write_text(
        json.dumps(fleet_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nDone. {len(all_trips)} trips saved to {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
