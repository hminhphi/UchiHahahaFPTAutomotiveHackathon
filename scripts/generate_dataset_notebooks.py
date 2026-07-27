from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"


def md_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip("\n").splitlines(keepends=True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": source.strip("\n").splitlines(keepends=True),
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


COMMON_SETUP = """
from pathlib import Path
import sys

PROJECT_ROOT = Path.cwd().resolve()
if not (PROJECT_ROOT / "AGENTS.md").exists():
    if (PROJECT_ROOT.parent / "AGENTS.md").exists():
        PROJECT_ROOT = PROJECT_ROOT.parent
    else:
        raise FileNotFoundError("Cannot locate project root from the current notebook working directory.")

NOTEBOOK_HELPERS = PROJECT_ROOT / "notebooks"
if str(NOTEBOOK_HELPERS) not in sys.path:
    sys.path.insert(0, str(NOTEBOOK_HELPERS))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import fleetiq_notebook_utils as nb

plt.style.use("seaborn-v0_8-whitegrid")
pd.set_option("display.max_columns", 120)
pd.set_option("display.width", 160)
"""


NB1 = notebook(
    [
        md_cell(
            """
# Dataset Inventory & Data Quality

Notebook này quét toàn bộ dataset hiện có trong `data/`, đối chiếu practice và redacted, rồi chỉ ra các điểm đáng chú ý cho team:

- số trip, số frame, độ dài, FPS
- mức độ đầy đủ của từng modality
- trip nào có/không có driver label hoặc risk ground truth
- coverage của image/depth/label/calibration
"""
        ),
        code_cell(COMMON_SETUP),
        code_cell(
            """
inventory = nb.build_dataset_inventory()
inventory
"""
        ),
        code_cell(
            """
inventory.groupby("dataset_name")[
    [
        "frame_count",
        "duration_sec",
        "event_log_count",
        "left_images",
        "right_images",
        "driver_images",
        "depth_files",
        "label_files",
    ]
].agg(["count", "sum", "mean"])
"""
        ),
        code_cell(
            """
anomalies = inventory.assign(
    missing_driver_labels=lambda df: ~df["driver_labels_available"],
    missing_risk_gt=lambda df: ~df["risk_ground_truth_available"],
    partial_road_assets=lambda df: (df["left_image_coverage"] < 1.0) | (df["right_image_coverage"] < 1.0),
    sparse_depth=lambda df: df["depth_coverage"] < 1.0,
    sparse_labels=lambda df: df["label_coverage"] < 1.0,
)
anomalies[
    [
        "trip_id",
        "dataset_name",
        "frame_count",
        "driver_labels_available",
        "risk_ground_truth_available",
        "left_image_coverage",
        "right_image_coverage",
        "driver_image_coverage",
        "depth_coverage",
        "label_coverage",
        "partial_road_assets",
        "sparse_depth",
        "sparse_labels",
    ]
]
"""
        ),
        code_cell(
            """
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

inventory.plot.bar(x="trip_id", y="frame_count", color="#034EA2", ax=axes[0], legend=False)
axes[0].set_title("Frame count per trip")
axes[0].tick_params(axis="x", rotation=75)

coverage_cols = ["left_image_coverage", "driver_image_coverage", "depth_coverage", "label_coverage"]
inventory.set_index("trip_id")[coverage_cols].plot.bar(ax=axes[1])
axes[1].set_title("Modality coverage ratio")
axes[1].tick_params(axis="x", rotation=75)

inventory.groupby("dataset_name")[["driver_labels_available", "risk_ground_truth_available"]].mean().plot.bar(
    ax=axes[2], color=["#F37021", "#19226D"]
)
axes[2].set_title("Ground-truth availability")
axes[2].set_ylim(0, 1.05)
axes[2].legend(loc="lower right")

plt.tight_layout()
"""
        ),
        code_cell(
            """
trip_paths = nb.canonical_trip_paths()
trip_paths
"""
        ),
        code_cell(
            """
out_path = PROJECT_ROOT / "artifacts" / "dataset_inventory.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
inventory.to_csv(out_path, index=False)
out_path
"""
        ),
    ]
)


NB2 = notebook(
    [
        md_cell(
            """
# Practice Dataset Statistics

Notebook này chỉ tập trung vào `Practice_Dataset` vì đây là phần có đủ ground truth driver để:

- thống kê phân bố label
- xem phân bố theo trip và theo subject
- phân tích alertness, transition và segment
- chuẩn bị training index / grouped validation về sau
"""
        ),
        code_cell(COMMON_SETUP),
        code_cell(
            """
practice_df = nb.build_practice_frame_index()
practice_df.head()
"""
        ),
        code_cell(
            """
dist = nb.state_distribution_tables(practice_df)
dist["overall"]
"""
        ),
        code_cell(
            """
dist["by_trip"]
"""
        ),
        code_cell(
            """
dist["by_subject"]
"""
        ),
        code_cell(
            """
alertness_stats = (
    practice_df.groupby("driver_state")["alertness_score"]
    .agg(["count", "mean", "std", "min", "median", "max"])
    .sort_values("mean")
)
alertness_stats
"""
        ),
        code_cell(
            """
transition_matrix = nb.compute_state_transitions(practice_df)
transition_pivot = transition_matrix.pivot(
    index="driver_state",
    columns="next_state",
    values="count",
).fillna(0).astype(int)
transition_pivot
"""
        ),
        code_cell(
            """
trip_id = "T01-Sample"
trip_df = practice_df.query("trip_id == @trip_id").copy()
segments = nb.derive_state_segments(trip_df)
segments
"""
        ),
        code_cell(
            """
fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)

state_order = ["alert", "drowsy", "yawning", "distracted", "microsleep"]
state_map = {state: idx for idx, state in enumerate(state_order)}

axes[0].plot(trip_df["timestamp"], trip_df["alertness_score"], color="#F37021", linewidth=2)
axes[0].set_ylabel("alertness_score")
axes[0].set_title(f"Alertness timeline | {trip_id}")

axes[1].step(
    trip_df["timestamp"],
    trip_df["driver_state"].map(state_map),
    where="post",
    color="#19226D",
    linewidth=2,
)
axes[1].set_yticks(list(state_map.values()))
axes[1].set_yticklabels(state_order)
axes[1].set_ylabel("driver_state")
axes[1].set_xlabel("timestamp (s)")
axes[1].set_title(f"State timeline | {trip_id}")

plt.tight_layout()
"""
        ),
        code_cell(
            """
out_dir = PROJECT_ROOT / "artifacts" / "practice_stats"
out_dir.mkdir(parents=True, exist_ok=True)
practice_df.to_csv(out_dir / "practice_frame_index.csv", index=False)
segments.to_csv(out_dir / f"{trip_id}_segments.csv", index=False)
alertness_stats.to_csv(out_dir / "alertness_stats.csv")
out_dir
"""
        ),
    ]
)


NB3 = notebook(
    [
        md_cell(
            """
# Frame Synchronization & Canonical Timeline

Notebook này tạo một bảng synchronized theo `frame_id` cho từng trip, gom về cùng một timeline:

- telemetry từ `ego`
- driver labels / confidence-like fields nếu có
- risk / TTC ground truth nếu có
- target summary
- modality availability theo frame
- event log gần nhất theo timestamp

Mục tiêu là tạo nền tảng cho API, analytics và unified event schema về sau.
"""
        ),
        code_cell(COMMON_SETUP),
        code_cell(
            """
practice_trip = "T01-Sample"
practice_dir = nb.practice_root() / practice_trip
sync_df = nb.build_sync_frame_table(practice_dir)
sync_df.head()
"""
        ),
        code_cell(
            """
nb.sync_quality_summary(sync_df)
"""
        ),
        code_cell(
            """
nb.build_event_log_table(practice_dir)
"""
        ),
        code_cell(
            """
fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)

axes[0].plot(sync_df["timestamp"], sync_df["speed_kmh"], color="#034EA2", linewidth=1.8)
axes[0].set_ylabel("speed_kmh")
axes[0].set_title(f"Synchronized timeline | {practice_trip}")

axes[1].plot(sync_df["timestamp"], sync_df["alertness_score"], color="#F37021", linewidth=1.8)
axes[1].set_ylabel("alertness")

axes[2].plot(sync_df["timestamp"], sync_df["min_ttc"], color="#D64545", linewidth=1.8)
axes[2].set_ylabel("min_ttc")

axes[3].plot(sync_df["timestamp"], sync_df["final_risk_score"], color="#19226D", linewidth=1.8)
axes[3].set_ylabel("risk")
axes[3].set_xlabel("timestamp (s)")

for ax in axes:
    ax.grid(True, alpha=0.3)

plt.tight_layout()
"""
        ),
        code_cell(
            """
target_class_counts = nb.count_target_classes(sync_df)
target_class_counts
"""
        ),
        code_cell(
            """
frame_id = 300
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, stream in zip(axes, ["left", "right", "driver"]):
    image = nb.load_trip_image(practice_dir, frame_id, stream=stream)
    ax.imshow(image)
    ax.set_title(f"{stream} | frame {frame_id}")
    ax.axis("off")
plt.tight_layout()
"""
        ),
        code_cell(
            """
redacted_trip = "T01d"
redacted_dir = nb.redacted_root() / redacted_trip
redacted_sync = nb.build_sync_frame_table(redacted_dir)

redacted_sync[
    [
        "trip_id",
        "frame_id",
        "timestamp",
        "speed_kmh",
        "driver_state",
        "min_ttc",
        "final_risk_score",
        "target_count",
        "target_classes",
        "has_left_image",
        "has_driver_image",
    ]
].head()
"""
        ),
        code_cell(
            """
out_dir = PROJECT_ROOT / "artifacts" / "sync_tables"
out_dir.mkdir(parents=True, exist_ok=True)
sync_df.to_csv(out_dir / f"{practice_trip}_sync.csv", index=False)
redacted_sync.to_csv(out_dir / f"{redacted_trip}_sync.csv", index=False)
out_dir
"""
        ),
    ]
)


def write_notebook(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    write_notebook(NOTEBOOK_DIR / "01_dataset_inventory.ipynb", NB1)
    write_notebook(NOTEBOOK_DIR / "02_practice_driver_statistics.ipynb", NB2)
    write_notebook(NOTEBOOK_DIR / "03_frame_synchronization.ipynb", NB3)


if __name__ == "__main__":
    main()
