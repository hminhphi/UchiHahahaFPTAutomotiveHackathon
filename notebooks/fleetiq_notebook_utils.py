from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency in user env
    Image = None


def project_root() -> Path:
    here = Path.cwd().resolve()
    candidates = [here, *here.parents]
    for candidate in candidates:
        if (candidate / "AGENTS.md").exists():
            return candidate
    raise FileNotFoundError("Cannot locate project root containing AGENTS.md")


def practice_root() -> Path:
    return project_root() / "data" / "Practice_Dataset" / "Practice_Dataset"


def redacted_root() -> Path:
    return (
        project_root()
        / "data"
        / "Hackathon_Dataset_Redacted"
        / "Hackathon_Dataset_Redacted"
    )


def list_trip_dirs(root: Path) -> list[Path]:
    return sorted([path for path in root.iterdir() if path.is_dir()])


def load_trip_json(trip_dir: Path) -> dict[str, Any]:
    json_path = trip_dir / f"{trip_dir.name}.json.gz"
    with gzip.open(json_path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def dataset_name_for_trip(trip_dir: Path) -> str:
    if trip_dir.name.endswith("-Sample"):
        return "practice"
    return "redacted"


def _glob_count(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob(pattern))


def _safe_get(mapping: dict[str, Any] | None, key: str, default: Any = np.nan) -> Any:
    if isinstance(mapping, dict):
        return mapping.get(key, default)
    return default


def _driver_image_path(trip_dir: Path, frame_id: int) -> Path | None:
    stems = [f"frame_{frame_id:06d}", f"{frame_id:06d}"]
    exts = [".jpg", ".jpeg", ".png"]
    for stem in stems:
        for ext in exts:
            candidate = trip_dir / "driver" / f"{stem}{ext}"
            if candidate.exists():
                return candidate
    return None


def summarize_trip(trip_dir: Path) -> dict[str, Any]:
    trip = load_trip_json(trip_dir)
    frames = trip.get("frames", [])
    frame_count = len(frames)
    timestamps = [frame.get("timestamp", np.nan) for frame in frames]
    duration_sec = float(timestamps[-1]) if timestamps else 0.0
    deltas = np.diff(timestamps).tolist() if len(timestamps) > 1 else []
    driver_frames = [
        frame
        for frame in frames
        if isinstance(frame.get("driver"), dict) and frame.get("driver")
    ]
    risk_frames = [frame for frame in frames if isinstance(frame.get("risk"), dict)]
    target_counts = [len(frame.get("targets", [])) for frame in frames]
    active_event_counts = [len(frame.get("events_active", [])) for frame in frames]

    return {
        "trip_id": trip.get("trip_id", trip_dir.name),
        "dataset_name": dataset_name_for_trip(trip_dir),
        "frame_count": frame_count,
        "duration_sec": duration_sec,
        "fps_estimate": round(1.0 / float(np.median(deltas)), 2) if deltas else np.nan,
        "driver_labels_available": bool(driver_frames and driver_frames[0].get("driver")),
        "risk_ground_truth_available": bool(risk_frames),
        "trip_aggregate_available": "trip_aggregate" in trip,
        "driver_summary_available": "driver_summary" in trip,
        "event_log_count": len(trip.get("events_log", [])),
        "target_count_mean": float(np.mean(target_counts)) if target_counts else 0.0,
        "target_count_max": int(np.max(target_counts)) if target_counts else 0,
        "events_active_max": int(np.max(active_event_counts)) if active_event_counts else 0,
        "left_images": _glob_count(trip_dir / "kitti" / "image_2", "*.jpg"),
        "right_images": _glob_count(trip_dir / "kitti" / "image_3", "*.jpg"),
        "driver_images": _glob_count(trip_dir / "driver", "*.jpg"),
        "depth_files": _glob_count(trip_dir / "kitti" / "depth", "*.npy"),
        "calib_files": _glob_count(trip_dir / "kitti" / "calib", "*.txt"),
        "label_files": _glob_count(trip_dir / "kitti" / "label_2", "*.txt"),
    }


def build_dataset_inventory() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for root in [practice_root(), redacted_root()]:
        for trip_dir in list_trip_dirs(root):
            rows.append(summarize_trip(trip_dir))
    inventory = pd.DataFrame(rows).sort_values(["dataset_name", "trip_id"]).reset_index(drop=True)
    if not inventory.empty:
        inventory["left_image_coverage"] = inventory["left_images"] / inventory["frame_count"]
        inventory["right_image_coverage"] = inventory["right_images"] / inventory["frame_count"]
        inventory["driver_image_coverage"] = inventory["driver_images"] / inventory["frame_count"]
        inventory["depth_coverage"] = inventory["depth_files"] / inventory["frame_count"]
        inventory["label_coverage"] = inventory["label_files"] / inventory["frame_count"]
    return inventory


def build_event_log_table(trip_dir: Path) -> pd.DataFrame:
    trip = load_trip_json(trip_dir)
    rows = []
    for event in trip.get("events_log", []):
        row = {
            "trip_id": trip.get("trip_id", trip_dir.name),
            "event_t": event.get("t", np.nan),
            "event_type": event.get("type", ""),
        }
        params = event.get("params", {})
        if isinstance(params, dict):
            for key, value in params.items():
                row[f"param_{key}"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def build_sync_frame_table(trip_dir: Path) -> pd.DataFrame:
    trip = load_trip_json(trip_dir)
    rows: list[dict[str, Any]] = []
    for frame in trip.get("frames", []):
        driver = frame.get("driver", {}) if isinstance(frame.get("driver"), dict) else {}
        ego = frame.get("ego", {}) if isinstance(frame.get("ego"), dict) else {}
        risk = frame.get("risk", {}) if isinstance(frame.get("risk"), dict) else {}
        behavior = (
            frame.get("behavior_flags", {})
            if isinstance(frame.get("behavior_flags"), dict)
            else {}
        )
        targets = frame.get("targets", []) if isinstance(frame.get("targets"), list) else []
        active = frame.get("events_active", []) if isinstance(frame.get("events_active"), list) else []

        target_classes = [
            target.get("target_class", "unknown")
            for target in targets
            if isinstance(target, dict)
        ]
        target_ids = [
            str(target.get("target_id", "unknown"))
            for target in targets
            if isinstance(target, dict)
        ]
        ttc_values = [
            target.get("ttc_2d")
            for target in targets
            if isinstance(target, dict) and isinstance(target.get("ttc_2d"), (int, float))
        ]
        long_distances = [
            target.get("longitudinal_distance")
            for target in targets
            if isinstance(target, dict)
            and isinstance(target.get("longitudinal_distance"), (int, float))
        ]

        row = {
            "trip_id": trip.get("trip_id", trip_dir.name),
            "dataset_name": dataset_name_for_trip(trip_dir),
            "frame_id": frame.get("frame_id"),
            "world_frame": frame.get("world_frame", np.nan),
            "timestamp": frame.get("timestamp", np.nan),
            "speed_kmh": _safe_get(ego, "speed_kmh"),
            "longitudinal_accel": _safe_get(ego, "longitudinal_accel"),
            "lateral_accel": _safe_get(ego, "lateral_accel"),
            "driver_state": _safe_get(driver, "state"),
            "alertness_score": _safe_get(driver, "alertness_score"),
            "eye_state": _safe_get(driver, "eye_state"),
            "head_pose": _safe_get(driver, "head_pose"),
            "mouth_state": _safe_get(driver, "mouth_state"),
            "subject_id": _safe_get(driver, "nthu_subject_id"),
            "min_ttc": frame.get("min_ttc", np.nan),
            "headway_sec": frame.get("headway_sec", np.nan),
            "base_risk": _safe_get(risk, "base_risk"),
            "driver_factor": _safe_get(risk, "driver_factor"),
            "final_risk_score": _safe_get(risk, "final_risk_score"),
            "is_harsh_brake": _safe_get(behavior, "harsh_brake", False),
            "is_harsh_accel": _safe_get(behavior, "harsh_accel", False),
            "is_harsh_corner": _safe_get(behavior, "harsh_corner", False),
            "is_speeding": _safe_get(behavior, "speeding", False),
            "is_tailgating": _safe_get(behavior, "tailgating", False),
            "target_count": len(targets),
            "target_classes": "|".join(sorted(set(target_classes))) if target_classes else "",
            "target_ids_sample": "|".join(target_ids[:5]) if target_ids else "",
            "target_min_ttc_2d": float(np.nanmin(ttc_values)) if ttc_values else np.nan,
            "target_min_longitudinal_distance": (
                float(np.nanmin(long_distances)) if long_distances else np.nan
            ),
            "events_active_count": len(active),
            "events_active_types": "|".join(_extract_event_types(active)),
            "has_left_image": (trip_dir / "kitti" / "image_2" / f"{frame['frame_id']:06d}.jpg").exists(),
            "has_right_image": (trip_dir / "kitti" / "image_3" / f"{frame['frame_id']:06d}.jpg").exists(),
            "has_driver_image": _driver_image_path(trip_dir, int(frame["frame_id"])) is not None,
            "has_depth": (trip_dir / "kitti" / "depth" / f"{frame['frame_id']:06d}.npy").exists(),
            "has_calib": (trip_dir / "kitti" / "calib" / f"{frame['frame_id']:06d}.txt").exists(),
            "has_label": (trip_dir / "kitti" / "label_2" / f"{frame['frame_id']:06d}.txt").exists(),
        }
        rows.append(row)

    table = pd.DataFrame(rows).sort_values("frame_id").reset_index(drop=True)
    if not table.empty:
        table["dt"] = table["timestamp"].diff()
        event_log = build_event_log_table(trip_dir)
        if not event_log.empty:
            event_log = event_log.sort_values("event_t").reset_index(drop=True)
            table = pd.merge_asof(
                table.sort_values("timestamp"),
                event_log[["event_t", "event_type"]].sort_values("event_t"),
                left_on="timestamp",
                right_on="event_t",
                direction="backward",
                tolerance=0.5,
            ).rename(columns={"event_type": "last_event_type"})
    return table


def _extract_event_types(active_events: list[Any]) -> list[str]:
    event_types: list[str] = []
    for event in active_events:
        if isinstance(event, dict):
            event_types.append(str(event.get("type", "unknown")))
        else:
            event_types.append(str(event))
    return sorted(set(event_types))


def build_practice_frame_index() -> pd.DataFrame:
    frames = [
        build_sync_frame_table(trip_dir)
        for trip_dir in list_trip_dirs(practice_root())
    ]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def state_distribution_tables(practice_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    clean = practice_df.dropna(subset=["driver_state"]).copy()
    overall = (
        clean.groupby("driver_state")
        .size()
        .rename("frame_count")
        .reset_index()
        .sort_values("frame_count", ascending=False)
    )
    overall["ratio"] = overall["frame_count"] / overall["frame_count"].sum()

    by_trip = (
        clean.pivot_table(
            index="trip_id",
            columns="driver_state",
            values="frame_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    by_subject = (
        clean.pivot_table(
            index="subject_id",
            columns="driver_state",
            values="frame_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    return {"overall": overall, "by_trip": by_trip, "by_subject": by_subject}


def compute_state_transitions(practice_df: pd.DataFrame) -> pd.DataFrame:
    clean = practice_df.dropna(subset=["driver_state"]).sort_values(["trip_id", "frame_id"]).copy()
    clean["next_state"] = clean.groupby("trip_id")["driver_state"].shift(-1)
    transitions = clean.dropna(subset=["next_state"])
    matrix = (
        transitions.groupby(["driver_state", "next_state"])
        .size()
        .rename("count")
        .reset_index()
    )
    return matrix


def derive_state_segments(trip_df: pd.DataFrame) -> pd.DataFrame:
    if trip_df.empty:
        return pd.DataFrame()
    ordered = trip_df.sort_values("frame_id").reset_index(drop=True).copy()
    ordered["state_change"] = ordered["driver_state"].ne(ordered["driver_state"].shift())
    ordered["segment_id"] = ordered["state_change"].cumsum()
    segments = (
        ordered.groupby(["trip_id", "segment_id", "driver_state"], dropna=False)
        .agg(
            start_frame=("frame_id", "min"),
            end_frame=("frame_id", "max"),
            start_ts=("timestamp", "min"),
            end_ts=("timestamp", "max"),
            frame_count=("frame_id", "count"),
            min_alertness=("alertness_score", "min"),
            mean_speed_kmh=("speed_kmh", "mean"),
        )
        .reset_index()
    )
    segments["duration_sec"] = segments["end_ts"] - segments["start_ts"] + 0.05
    return segments


def sync_quality_summary(sync_df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trip_id": sync_df["trip_id"].iloc[0] if not sync_df.empty else "",
                "frame_rows": len(sync_df),
                "missing_left_images": int((~sync_df["has_left_image"]).sum()),
                "missing_right_images": int((~sync_df["has_right_image"]).sum()),
                "missing_driver_images": int((~sync_df["has_driver_image"]).sum()),
                "missing_depth_files": int((~sync_df["has_depth"]).sum()),
                "missing_label_files": int((~sync_df["has_label"]).sum()),
                "missing_calib_files": int((~sync_df["has_calib"]).sum()),
                "has_driver_state_labels": bool(sync_df["driver_state"].notna().any()),
                "has_risk_ground_truth": bool(sync_df["final_risk_score"].notna().any()),
                "target_count_mean": float(sync_df["target_count"].mean()) if not sync_df.empty else 0.0,
                "dt_median": float(sync_df["dt"].dropna().median()) if "dt" in sync_df else np.nan,
            }
        ]
    )


def load_trip_image(trip_dir: Path, frame_id: int, stream: str = "driver"):
    if Image is None:
        raise ImportError("Pillow is required to load images in this notebook")

    subdir = {
        "driver": trip_dir / "driver",
        "left": trip_dir / "kitti" / "image_2",
        "right": trip_dir / "kitti" / "image_3",
    }[stream]
    if stream == "driver":
        image_path = _driver_image_path(trip_dir, frame_id)
        if image_path is None:
            raise FileNotFoundError(f"Driver image not found for frame_id={frame_id} in {trip_dir}")
    else:
        image_path = subdir / f"{frame_id:06d}.jpg"
    return Image.open(image_path)


def canonical_trip_paths() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for root in [practice_root(), redacted_root()]:
        for trip_dir in list_trip_dirs(root):
            rows.append(
                {
                    "trip_id": trip_dir.name,
                    "dataset_name": dataset_name_for_trip(trip_dir),
                    "trip_dir": str(trip_dir),
                    "json_path": str(trip_dir / f"{trip_dir.name}.json.gz"),
                }
            )
    return pd.DataFrame(rows).sort_values(["dataset_name", "trip_id"]).reset_index(drop=True)


def flatten_trip_metadata(trip_dir: Path) -> pd.DataFrame:
    trip = load_trip_json(trip_dir)
    metadata = trip.get("metadata", {})
    row = {"trip_id": trip.get("trip_id", trip_dir.name)}
    for key, value in metadata.items():
        row[f"metadata_{key}"] = value
    return pd.DataFrame([row])


def count_target_classes(sync_df: pd.DataFrame) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for classes in sync_df["target_classes"].fillna(""):
        if not classes:
            continue
        for cls in classes.split("|"):
            counter[cls] += 1
    rows = [{"target_class": cls, "frame_mentions": count} for cls, count in counter.items()]
    return pd.DataFrame(rows).sort_values("frame_mentions", ascending=False).reset_index(drop=True)
