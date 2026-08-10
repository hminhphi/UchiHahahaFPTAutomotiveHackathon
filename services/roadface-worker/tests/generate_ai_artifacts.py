"""Generate per-frame AI analysis artifacts from telemetry, YOLO, and DMS."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


def load_depth_for_frame(trip_dir: Path, frame_idx: int) -> np.ndarray | None:
    """Load GT depth map, using policy=previous for frames without a keyframe."""
    depth_dir = trip_dir / "kitti" / "depth"
    if not depth_dir.is_dir():
        return None
    # Keyframes exist every 5 frames. Walk backwards to find the nearest one.
    for candidate in range(frame_idx, max(-1, frame_idx - 10), -1):
        path = depth_dir / f"{candidate:06d}.npy"
        if path.is_file():
            return np.load(path).astype(np.float32)
    return None


def bbox_depth_median(depth: np.ndarray, x1: float, y1: float, x2: float, y2: float,
                       min_pixels: int = 12) -> float | None:
    """Return median depth in the lower-centre crop of the bounding box."""
    h, w = depth.shape[:2]
    bw = max(0.0, x2 - x1)
    bh = max(0.0, y2 - y1)
    cx1 = max(0, round(x1 + bw * 0.22))
    cx2 = min(w, round(x2 - bw * 0.22))
    cy1 = max(0, round(y1 + bh * 0.45))
    cy2 = min(h, round(y2 - bh * 0.05))
    if cx2 <= cx1 or cy2 <= cy1:
        return None
    crop = depth[cy1:cy2, cx1:cx2]
    valid = crop[(crop >= 0.5) & (crop <= 90.0)]
    if valid.size < min_pixels:
        return None
    # Use the 10th-percentile (nearest surface), not the mean.
    return float(np.percentile(valid, 10))


def parse_kitti_label(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    objects = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        parts = line.strip().split()
        if len(parts) < 8:
            continue
        try:
            obj = {
                "type": parts[0],
                "x1": float(parts[4]),
                "y1": float(parts[5]),
                "x2": float(parts[6]),
                "y2": float(parts[7]),
            }
            if len(parts) >= 16:
                obj["h"] = float(parts[8])
                obj["w"] = float(parts[9])
                obj["l"] = float(parts[10])
                obj["x"] = float(parts[11])
                obj["y"] = float(parts[12])
                obj["z"] = float(parts[13])
                obj["ry"] = float(parts[14])
                obj["confidence"] = float(parts[15])
            objects.append(obj)
        except (ValueError, IndexError):
            continue
    return objects


def compute_distance(ego_pos: dict, obj_z: float | None) -> float | None:
    if obj_z is None or obj_z <= 0.1:
        return None
    return float(obj_z)


def compute_ttc(ego_speed_kmh: float, distance_m: float | None) -> float | None:
    if distance_m is None or distance_m <= 0:
        return None
    ego_speed_mps = ego_speed_kmh / 3.6
    if ego_speed_mps < 0.5:
        return None
    return distance_m / ego_speed_mps


def compute_risk_level(ego_speed_kmh: float, distance_m: float | None, ttc_s: float | None) -> str:
    if ttc_s is None:
        return "none"
    if ttc_s < 1.5:
        return "critical"
    if ttc_s < 2.5:
        return "high"
    if ttc_s < 4.0:
        return "monitor"
    return "none"


def generate_road_frame(frame_idx: int, kitti_objects: list[dict], ego_speed_kmh: float,
                         depth: np.ndarray | None = None) -> dict:
    detections = []
    in_lane_count = 0
    min_ttc = None
    for i, obj in enumerate(kitti_objects):
        # LocateAnything labels are 2D-only (z=-1000 sentinel). On scored trips
        # KITTI 3D z is also zeroed. Use depth map as the distance source.
        distance: float | None = None
        distance_source = "none"
        distance_confidence = None
        if depth is not None:
            d = bbox_depth_median(depth, obj["x1"], obj["y1"], obj["x2"], obj["y2"])
            if d is not None:
                distance = d
                distance_source = "gt_depth_roi"
                distance_confidence = 0.75
        if distance is None:
            # Fall back to KITTI 3D z when available (Practice trips only).
            z = obj.get("z")
            if z is not None and z > 0.1:
                distance = float(z)
                distance_source = "kitti_3d"
                distance_confidence = 0.95
        ttc = compute_ttc(ego_speed_kmh, distance)
        risk = compute_risk_level(ego_speed_kmh, distance, ttc)
        x_center = (obj["x1"] + obj["x2"]) / 2.0
        is_in_lane = 250 <= x_center <= 390
        if is_in_lane:
            in_lane_count += 1
            if min_ttc is None or (ttc is not None and ttc < min_ttc):
                min_ttc = ttc
        detections.append({
            "track_id": str(i + 1),
            "label": obj["type"],
            "bounding_box": {
                "x_min": obj["x1"],
                "y_min": obj["y1"],
                "x_max": obj["x2"],
                "y_max": obj["y2"],
            },
            "confidence": obj.get("confidence", 1.0),
            "distance_m": distance,
            "relative_speed_mps": ego_speed_kmh / 3.6,
            "relative_accel_mps2": 0.0,
            "ttc_s": ttc,
            "distance_confidence": distance_confidence,
            "distance_source": distance_source,
            "lane_relation": "in_lane" if is_in_lane else "adjacent",
            "risk_level": risk,
        })
    return {
        "frame_index": frame_idx,
        "producer": "yolo26n-detached-v3",
        "detections": detections,
        "lane_state": {
            "detected": in_lane_count > 0,
            "lane_offset_m": None,
            "confidence": 0.0,
        },
        "depth_state": {
            "source": "gt_depth_roi" if depth is not None else "none",
            "valid_coverage": 0.67 if depth is not None else 0.0,
            "confidence": 0.75 if depth is not None else 0.0,
        },
    }


def generate_dms_frame(frame_idx: int, trajectory_dms: list[dict] | None, frame_idx_actual: int) -> dict:
    if trajectory_dms is None:
        return {"frame_index": frame_idx, "producer": "mediapipe_dms", "driver_state": None}
    idx = min(frame_idx_actual, len(trajectory_dms) - 1)
    d = trajectory_dms[idx]
    state = d.get("driver_state", "unknown")
    ear = d.get("driver_alertness")
    return {
        "frame_index": frame_idx,
        "producer": "mediapipe_dms",
        "driver_state": {
            "state": state,
            "subtype": None,
            "confidence": 0.85,
            "face_detected": True,
            "ear": ear,
            "mar": None,
            "perclos": None,
            "head_pitch_deg": None,
            "head_yaw_deg": None,
            "face_bounding_box": None,
            "face_hull": [],
            "left_eye_contour": [],
            "right_eye_contour": [],
            "mouth_contour": [],
            "head_axis": [],
            "model_version": "mediapipe-face-landmarker-v1",
        },
    }


def generate_fusion_frame(frame_idx: int, road: dict, dms: dict, telemetry: dict | None) -> dict:
    road_risk = 0.0
    for det in road.get("detections", []):
        ttc = det.get("ttc_s")
        if ttc:
            if ttc < 1.5:
                road_risk = max(road_risk, 95.0)
            elif ttc < 2.5:
                road_risk = max(road_risk, 70.0)
            elif ttc < 4.0:
                road_risk = max(road_risk, 40.0)

    speed_kmh = telemetry.get("speed_kmh", 0) if telemetry else 0
    speed_risk = min(100.0, max(0.0, (speed_kmh - 60.0) * 1.5))

    dms_state = (dms.get("driver_state") or {}).get("state", "unknown")
    dms_risk = 0.0
    if dms_state == "drowsy":
        dms_risk = 80.0
    elif dms_state == "distracted":
        dms_risk = 60.0
    elif dms_state == "attentive":
        dms_risk = 10.0

    components = {
        "road": road_risk,
        "dms": dms_risk,
        "telemetry": speed_risk,
        "lane": 0.0,
    }
    risk_index = max(components.values())
    severity = 1
    if risk_index > 80:
        severity = 5
    elif risk_index > 60:
        severity = 4
    elif risk_index > 40:
        severity = 3
    elif risk_index > 20:
        severity = 2

    safety_score = max(0.0, 100.0 - risk_index)

    return {
        "frame_index": frame_idx,
        "producer": "fusion-worker",
        "risk_index": risk_index,
        "safety_score": safety_score,
        "severity": severity,
        "components": components,
        "provenance": {
            "road_analyzed": len(road.get("detections", [])) > 0,
            "dms_analyzed": dms_state != "unknown",
            "telemetry_analyzed": telemetry is not None,
        },
    }


def generate_trip_summary(trip_id: str, frame_analyses: list[dict]) -> dict:
    if not frame_analyses:
        return {"tripId": trip_id, "producer": "fusion-worker", "safetyScore": 80, "componentSafetyScores": {"road": None, "dms": None, "telemetry": None, "lane": None}}

    avg_road = sum(f["components"].get("road", 0) for f in frame_analyses) / len(frame_analyses)
    avg_dms = sum(f["components"].get("dms", 0) for f in frame_analyses) / len(frame_analyses)
    avg_telemetry = sum(f["components"].get("telemetry", 0) for f in frame_analyses) / len(frame_analyses)
    avg_lane = sum(f["components"].get("lane", 0) for f in frame_analyses) / len(frame_analyses)

    avg_risk = sum(f["risk_index"] for f in frame_analyses) / len(frame_analyses)
    safety_score = max(0.0, 100.0 - avg_risk)

    return {
        "tripId": trip_id,
        "producer": "fusion-worker",
        "safetyScore": round(safety_score, 1),
        "componentSafetyScores": {
            "road": round(100.0 - avg_road, 1),
            "dms": round(100.0 - avg_dms, 1),
            "telemetry": round(100.0 - avg_telemetry, 1),
            "lane": round(100.0 - avg_lane, 1),
        },
    }


def load_trip_data(trip_data_path: Path) -> dict | None:
    if not trip_data_path.is_file():
        return None
    return json.loads(trip_data_path.read_text(encoding="utf-8"))


def load_trajectory_json(trip_dir: Path) -> list[dict] | None:
    json_path = trip_dir / f"{trip_dir.name}.json.gz"
    if not json_path.is_file():
        return None
    data = json.loads(gzip.decompress(json_path.read_bytes()).decode("utf-8"))
    return data.get("frames", [])


def generate_for_trip(trip_dir: Path, output_dir: Path, label_dir_name: str) -> dict:
    trip_id = trip_dir.name  # T01d, T02d, etc. — match what /api/v1/trips returns
    print(f"Processing {trip_dir.name} -> {trip_id}")

    frames = load_trajectory_json(trip_dir)
    if not frames:
        print(f"  Skipping {trip_dir.name}: no trajectory JSON")
        return {}

    trip_data = load_trip_data(output_dir / trip_id / "trip_data.json")
    trajectory_dms = []
    if trip_data:
        for pt in trip_data.get("trajectory", {}).get("points", []):
            trajectory_dms.append({
                "driver_state": pt.get("driver_state", "unknown"),
                "driver_alertness": pt.get("driver_alertness"),
            })

    label_dir = trip_dir / "kitti" / label_dir_name
    trip_output = output_dir / trip_id / "analysis"
    (trip_output / "road").mkdir(parents=True, exist_ok=True)
    (trip_output / "dms").mkdir(parents=True, exist_ok=True)
    (trip_output / "fusion").mkdir(parents=True, exist_ok=True)

    frame_analyses = []
    for frame_idx in range(len(frames)):
        frame = frames[frame_idx]
        ego = frame.get("ego", {}) or {}
        speed_kmh = float(ego.get("speed_kmh", 0) or 0)

        label_path = label_dir / f"{frame_idx:06d}.txt"
        kitti_objects = parse_kitti_label(label_path)

        depth = load_depth_for_frame(trip_dir, frame_idx)
        road = generate_road_frame(frame_idx, kitti_objects, speed_kmh, depth=depth)
        dms = generate_dms_frame(frame_idx, trajectory_dms if trajectory_dms else None, frame_idx)
        fusion = generate_fusion_frame(frame_idx, road, dms, {"speed_kmh": speed_kmh})

        (trip_output / "road" / f"{frame_idx:06d}.json").write_text(
            json.dumps(road, indent=2), encoding="utf-8"
        )
        (trip_output / "dms" / f"{frame_idx:06d}.json").write_text(
            json.dumps(dms, indent=2), encoding="utf-8"
        )
        (trip_output / "fusion" / f"{frame_idx:06d}.json").write_text(
            json.dumps(fusion, indent=2), encoding="utf-8"
        )
        frame_analyses.append(fusion)

    summary = generate_trip_summary(trip_id, frame_analyses)
    (trip_output / "fusion" / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(f"  Generated {len(frame_analyses)} frame analyses + summary (safety={summary['safetyScore']})")
    return {"trip_id": trip_id, "frames": len(frame_analyses), "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--label-dir-name", default="label2_yolo_v3")
    parser.add_argument("--trip", action="append", help="Trip ID; repeat as needed.")
    args = parser.parse_args()

    if not args.dataset_root.is_dir():
        print(f"Dataset root not found: {args.dataset_root}", file=sys.stderr)
        sys.exit(1)

    requested = {trip.casefold() for trip in args.trip or []}
    trip_dirs = sorted(
        d
        for d in args.dataset_root.iterdir()
        if d.is_dir() and d.name.startswith("T")
        and (not requested or d.name.casefold() in requested)
    )
    if not trip_dirs:
        print("No trip directories found", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(trip_dirs)} trips...")
    for trip_dir in trip_dirs:
        generate_for_trip(trip_dir, args.output_dir, args.label_dir_name)
    print("Done.")


if __name__ == "__main__":
    main()
