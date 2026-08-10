"""Run FleetIQ's perception + DMS stacks to produce one trip's submission rows.

Kept separate from ``export_submission.py`` so the CSV format rules stay
importable (and unit-testable) without pulling in Torch, Ultralytics, OpenCV,
or MediaPipe.

Two properties matter for grading and are enforced here:

1. **Every frame gets a row.** The organizer checklist requires the CSV to
   have exactly the trip's frame count. Frames the perception stack cannot
   process (unreadable image, no detection, no face) still emit a row with
   ``inf`` TTC and a fallback driver state, rather than being dropped.
2. **TTC matches the ground truth's definition.** ``frame.min_ttc`` in the
   organizer's loader is the minimum over the *collision cone*, so
   ``frame_min_ttc`` filters to in-lane, distance-confident detections only.
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2

from fleetiq_data import DatasetPaths, load_trip_document, resolve_trip

from tools.dataset.export_submission import (
    FramePrediction,
    frame_min_ttc,
    write_submission_csv,
)

# Mirrors evaluation.py's Challenge 3 reconstruction, which is itself a copy of
# the organizer's BehaviorScorer thresholds. Risk score is a per-frame value in
# the CSV, but Challenge 3 is graded per trip and does not read these numbers
# (only the column's presence opts the trip in), so this stays a transparent
# severity signal rather than a fitted quantity.
_NEAR_MISS_TTC_SEC = 1.5
_HIGH_RISK_TTC_SEC = 2.5
_MONITOR_TTC_SEC = 4.0

_DROWSY_STATES = frozenset({"drowsy", "microsleep", "yawning"})


def _risk_score(min_ttc_s: float, driver_state: str) -> float:
    """Blend collision urgency with driver impairment into a 0-100 severity."""
    if math.isinf(min_ttc_s):
        road_risk = 0.0
    elif min_ttc_s < _NEAR_MISS_TTC_SEC:
        road_risk = 95.0
    elif min_ttc_s < _HIGH_RISK_TTC_SEC:
        road_risk = 70.0
    elif min_ttc_s < _MONITOR_TTC_SEC:
        road_risk = 40.0
    else:
        road_risk = 10.0

    if driver_state in _DROWSY_STATES:
        driver_risk = 80.0
    elif driver_state == "distracted":
        driver_risk = 60.0
    else:
        driver_risk = 10.0

    return max(road_risk, driver_risk)


def _driver_states(
    trip_dir: Path,
    frame_ids: list[int],
    dms_source: str,
    dms_checkpoint: Path | None,
) -> dict[int, str]:
    if dms_source == "model":
        if dms_checkpoint is None:
            raise ValueError(
                "--dms-checkpoint is required with --dms-source model. "
                "Pass --dms-source pseudo_label to use the rule-based labels."
            )
        from fleetiq_training_dms.config import Config
        from fleetiq_training_dms.dataset import FEATURE_COLS
        from fleetiq_training_dms.model import build_sequence_model
        from fleetiq_training_dms.predict import predict_sequence_trip
        import torch

        model = build_sequence_model(
            feature_dim=len(FEATURE_COLS),
            hidden_dim=Config.HIDDEN_DIM,
            num_layers=Config.NUM_LAYERS,
            num_classes=Config.NUM_CLASSES,
            cell_type=Config.MODEL_TYPE,
        ).to(Config.DEVICE)
        checkpoint = torch.load(dms_checkpoint, map_location=Config.DEVICE, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        frame = predict_sequence_trip(
            model,
            trip_dir,
            seq_len=Config.SEQ_LEN,
            mean_scaler=checkpoint.get("mean_scaler"),
            std_scaler=checkpoint.get("std_scaler"),
            device=Config.DEVICE,
        )
        return {
            int(row["frame_id"]): str(row["predicted_driver_state"])
            for _, row in frame.iterrows()
        }

    from fleetiq_training_dms.feature_extractor import extract_features_from_trip
    from fleetiq_training_dms.pseudo_labels import STATE_MAP, apply_geometry_pseudo_labels

    inverse_states = {value: key for key, value in STATE_MAP.items()}
    features = extract_features_from_trip(trip_dir, is_train=False)
    labelled = apply_geometry_pseudo_labels(features)
    return {
        int(row["frame_id"]): inverse_states.get(int(row["state_label"]), "alert")
        for _, row in labelled.iterrows()
    }


def _min_ttc_by_frame(
    trip_id: str,
    dataset_root: Path,
    yolo_weights: Path | None,
) -> dict[int, float]:
    from fleetiq_roadface.pipeline import PipelineOptions, RoadfacePipeline
    from fleetiq_roadface.yolo_detector import YoloDetector

    dataset = DatasetPaths(dataset_root)
    pipeline = RoadfacePipeline(
        dataset_paths=dataset,
        output_root=Path("artifacts/predictions/roadface/submission"),
        detector=YoloDetector(
            weights_path=yolo_weights,
            device="0",
            confidence_threshold=0.25,
        ),
        depth_model=None,
    )
    options = PipelineOptions(
        detector_source="model",
        # LocateAnything/YOLO boxes are 2D only; the scored trips also zero out
        # KITTI 3D location, so distance has to come from the stereo pair.
        depth_source="stereo",
        # Classical Hough-transform lane detection only succeeds on a
        # fraction of frames in practice (measured ~20% on T01-Sample), which
        # would silently drop most of the collision-critical frames if TTC
        # were gated on lane_relation=="in_lane". frame_min_ttc instead uses
        # a fixed centered ROI, so lane output isn't needed for TTC.
        lane_method="classical",
        lane_filter=False,
        visualize=False,
    )

    trip = pipeline.resolve_trip(trip_id)
    document = load_trip_document(trip)
    raw_frames = document.get("frames", [])

    first_image = cv2.imread(str(sorted(trip.image_2_dir.iterdir())[0]))
    if first_image is None:
        raise RuntimeError(f"Cannot read any road image for {trip_id}")
    image_height, image_width = first_image.shape[:2]

    ttc_by_frame: dict[int, float] = {}
    for processing_index, raw_frame in enumerate(raw_frames):
        frame_id = int(raw_frame.get("frame_id", processing_index))
        result = pipeline.process_frame(
            trip,
            frame=raw_frame,
            frame_index=frame_id,
            processing_index=processing_index,
            fps=20.0,
            options=options,
        )
        if result is None:
            ttc_by_frame[frame_id] = float("inf")
            continue
        ttc_by_frame[frame_id] = frame_min_ttc(
            [
                {
                    "bbox": detection.bbox,
                    "ttc_s": detection.ttc_s,
                    "distance_confidence": detection.distance_confidence,
                }
                for detection in result.detections
            ],
            image_width=image_width,
            image_height=image_height,
        )
    return ttc_by_frame


def export_trip(
    *,
    trip_id: str,
    dataset_root: Path,
    output_path: Path,
    dms_checkpoint: Path | None,
    dms_source: str,
    yolo_weights: Path | None,
) -> Path:
    trip = resolve_trip(DatasetPaths(dataset_root), trip_id)
    document = load_trip_document(trip)
    raw_frames = document.get("frames", [])
    if not raw_frames:
        raise ValueError(f"Trip {trip_id} has no frames")

    ttc_by_frame = _min_ttc_by_frame(trip_id, dataset_root, yolo_weights)
    frame_ids = [
        int(raw_frame.get("frame_id", index)) for index, raw_frame in enumerate(raw_frames)
    ]
    states_by_frame = _driver_states(trip.trip_dir, frame_ids, dms_source, dms_checkpoint)

    predictions: list[FramePrediction] = []
    for index, raw_frame in enumerate(raw_frames):
        frame_id = int(raw_frame.get("frame_id", index))
        timestamp_s = float(raw_frame.get("timestamp", index / 20.0))
        min_ttc = ttc_by_frame.get(frame_id, float("inf"))
        driver_state = states_by_frame.get(frame_id, "alert")
        predictions.append(
            FramePrediction(
                frame_id=frame_id,
                timestamp_s=timestamp_s,
                predicted_ttc_s=min_ttc,
                predicted_driver_state=driver_state,
                predicted_risk_score=_risk_score(min_ttc, driver_state),
            )
        )

    write_submission_csv(output_path, predictions)
    return output_path
