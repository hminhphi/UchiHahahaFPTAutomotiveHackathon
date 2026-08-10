"""Enrich detached trip documents with trip_aggregate and driver_summary.

Uses existing trip_data.json from artifacts/trips/ as the source of trajectory
and driver state data (already computed by generate_trip_data.py).

Usage:
    uv run python services/roadface-worker/tests/enrich_detached_trips.py
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

HACKATHON_ROOT = Path("data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted")
ARTIFACTS_TRIPS = Path("artifacts/trips")
OUTPUT_ROOT = ARTIFACTS_TRIPS


def compute_trip_aggregate(frames: list[dict], trajectory_points: list[dict]) -> dict:
    speeds = []
    long_accels = []
    lat_accels = []
    ttc_values = []
    risk_scores = []

    for f in frames:
        ego = f.get("ego", {}) or {}
        sp = ego.get("speed_kmh")
        if sp is not None and np.isfinite(float(sp)):
            speeds.append(float(sp))
        la = ego.get("longitudinal_accel")
        if la is not None and np.isfinite(float(la)):
            long_accels.append(float(la))
        la2 = ego.get("lateral_accel")
        if la2 is not None and np.isfinite(float(la2)):
            lat_accels.append(float(la2))

    for pt in trajectory_points:
        ttc = pt.get("min_ttc_s")
        if ttc is not None and np.isfinite(float(ttc)):
            ttc_values.append(float(ttc))
        risk = pt.get("simulator_risk_score")
        if risk is not None and np.isfinite(float(risk)):
            risk_scores.append(float(risk))

    harsh_brake = sum(1 for a in long_accels if a <= -4.0)
    harsh_accel = sum(1 for a in long_accels if a >= 4.0)
    harsh_corner = sum(1 for a in lat_accels if abs(a) >= 3.0)
    near_miss = sum(1 for t in ttc_values if t < 1.5)
    speeding = sum(1 for s in speeds if s > 60)
    speeding_pct = round(speeding / len(speeds) * 100, 1) if speeds else 0.0

    max_risk = round(max(risk_scores), 1) if risk_scores else 0.0
    avg_risk = round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0.0

    return {
        "harsh_brake_count": harsh_brake,
        "harsh_accel_count": harsh_accel,
        "harsh_corner_count": harsh_corner,
        "near_miss_count": near_miss,
        "speeding_pct_time": speeding_pct,
        "tailgating_pct_time": 0.0,
        "avg_headway_sec": 1.5,
        "max_risk_score": max_risk,
        "avg_risk_score": avg_risk,
    }


def compute_driver_summary(trajectory_points: list[dict]) -> dict:
    states = Counter()
    alertness_values = []

    for pt in trajectory_points:
        state = pt.get("driver_state", "unknown")
        if state in {"microsleep", "yawning"}:
            state = "drowsy"
        elif state == "alert":
            state = "attentive"
        if state not in {"attentive", "distracted", "drowsy", "unknown"}:
            state = "unknown"
        states[state] += 1
        a = pt.get("driver_alertness")
        if a is not None and np.isfinite(float(a)):
            alertness_values.append(float(a))

    total = sum(states.values())
    state_pct = {k: round(v / total * 100, 1) for k, v in states.items()} if total else {}
    avg_alertness = round(sum(alertness_values) / len(alertness_values), 3) if alertness_values else 0.5

    return {
        "subject_id": "detached",
        "condition_subset": "Mixed",
        "state_distribution_pct": state_pct,
        "longest_drowsy_episode_sec": 0.0,
        "microsleep_count": 0,
        "average_alertness_score": avg_alertness,
        "fatigue_score": round((1 - avg_alertness) * 100, 1),
    }


def main() -> None:
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

        # Load existing trip_data.json for trajectory with DMS states
        trip_data_path = ARTIFACTS_TRIPS / trip_id / "trip_data.json"
        if not trip_data_path.is_file():
            print("  SKIP: no trip_data.json found")
            continue

        trip_data = json.loads(trip_data_path.read_text(encoding="utf-8"))
        trajectory = trip_data["trajectory"]["points"]

        data = json.loads(gzip.decompress(json_path.read_bytes()))
        frames = data.get("frames", [])
        print(f"  Frames: {len(frames)}, Trajectory points: {len(trajectory)}")

        trip_aggregate = compute_trip_aggregate(frames, trajectory)
        driver_summary = compute_driver_summary(trajectory)
        for raw_frame, point in zip(frames, trajectory):
            if not isinstance(raw_frame, dict):
                continue
            driver = raw_frame.get("driver")
            driver_data = dict(driver) if isinstance(driver, dict) else {}
            driver_data["state"] = point.get("driver_state", "unknown")
            raw_frame["driver"] = driver_data

        data["trip_aggregate"] = trip_aggregate
        data["driver_summary"] = driver_summary
        enriched_bytes = gzip.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        enriched_path = OUTPUT_ROOT / trip_id / f"{trip_id}.json.gz"
        enriched_path.parent.mkdir(parents=True, exist_ok=True)
        enriched_path.write_bytes(enriched_bytes)
        print(f"  Saved enriched: {enriched_path}")

        dominant_state = (
            max(driver_summary["state_distribution_pct"], key=driver_summary["state_distribution_pct"].get)
            if driver_summary["state_distribution_pct"]
            else "unknown"
        )

        # Keep dashboard metadata limited to source-backed trip evidence.
        trip_data["driver_state"] = dominant_state
        trip_data_path.write_text(json.dumps(trip_data, indent=2, ensure_ascii=False), encoding="utf-8")

        all_trips.append(trip_data)
        print(f"  Driver: {dominant_state}; aggregate evidence enriched")

    fleet_summary = {
        "trips": all_trips,
        "total": len(all_trips),
        "generated_at": str(datetime.now()),
    }
    (OUTPUT_ROOT / "fleet_summary.json").write_text(
        json.dumps(fleet_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nDone. {len(all_trips)} trips enriched -> {OUTPUT_ROOT}")

if __name__ == "__main__":
    main()
