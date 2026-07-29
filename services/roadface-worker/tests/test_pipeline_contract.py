from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fleetiq_contracts import InferenceResponse
from fleetiq_data import DatasetPaths
from fleetiq_roadface import pipeline
from fleetiq_roadface.pipeline import RoadfacePipeline
from fleetiq_roadface.tracking import ObstacleTracker
from fleetiq_roadface.types import (
    DepthEstimate,
    Detection,
    LaneEstimate,
    RoadFrameResult,
)


def test_frame_result_serializes_to_strict_inference_response() -> None:
    result = RoadFrameResult(
        request_id=UUID("00000000-0000-0000-0000-000000000004"),
        correlation_id="trip-1-frame-4",
        trip_id="trip-1",
        frame_index=4,
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
        detections=(
            Detection(
                object_type="Car",
                bbox=(1.0, 2.0, 11.0, 12.0),
                confidence=0.9,
                track_id=7,
                distance_m=18.0,
                relative_speed_mps=4.0,
                ttc_s=4.5,
            ),
        ),
        lane=LaneEstimate(
            detected=True,
            lane_offset_m=-0.2,
            heading_deg=1.5,
            confidence=0.8,
        ),
        depth=DepthEstimate(
            source="ground_truth",
            median_depth_m=18.0,
            valid_coverage=0.75,
            confidence=1.0,
        ),
    )

    response = result.to_inference_response()
    payload = response.model_dump(mode="json")

    assert isinstance(response, InferenceResponse)
    assert set(payload) == {
        "schema_version",
        "request_id",
        "correlation_id",
        "trip_id",
        "frame_index",
        "producer",
        "occurred_at",
        "detections",
        "lane_state",
        "depth_state",
        "driver_state",
    }
    assert payload["schema_version"] == "1.0"
    assert set(payload["detections"][0]) == {
        "track_id",
        "label",
        "bounding_box",
        "confidence",
        "distance_m",
        "relative_speed_mps",
        "ttc_s",
    }
    InferenceResponse.model_validate(payload)
    json.dumps(payload, allow_nan=False)


def test_pipeline_requires_explicit_paths_and_model_dependencies(
    tmp_path: Path,
) -> None:
    pipeline = RoadfacePipeline(
        dataset_paths=DatasetPaths(tmp_path / "dataset"),
        output_root=tmp_path / "output",
        detector=None,
        depth_model=None,
    )

    assert pipeline.dataset_paths.root == tmp_path / "dataset"
    assert pipeline.output_root == tmp_path / "output"


def test_frame_range_filters_and_sorts_organizer_frame_ids() -> None:
    frames = [
        {"frame_id": 120, "timestamp": 12.0},
        {"frame_id": 90, "timestamp": 9.0},
        {"frame_id": 105, "timestamp": 10.5},
    ]

    selected = pipeline._select_frames(frames, start=90, end=120, stride=2)

    assert [frame_id for frame_id, _, _ in selected] == [90, 120]


def test_sparse_nonzero_frame_range_does_not_use_list_positions() -> None:
    frames = [
        {"frame_id": 90},
        {"frame_id": 105},
        {"frame_id": 120},
    ]

    selected = pipeline._select_frames(frames, start=100, end=110, stride=1)

    assert [frame_id for frame_id, _, _ in selected] == [105]


def test_sorted_frames_use_monotonic_processing_time_fallback() -> None:
    frames = [
        {"frame_id": 120, "timestamp": "invalid"},
        {"frame_id": 90},
        {"frame_id": 105, "timestamp": None},
    ]

    selected = pipeline._select_frames(frames, start=0, end=None, stride=1)
    timestamps = [
        pipeline._timestamp_s(frame, processing_index, fps=10.0)
        for _, processing_index, frame in selected
    ]
    occurred_at = [
        datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=value)
        for value in timestamps
    ]

    assert occurred_at == sorted(occurred_at)
    assert len(set(occurred_at)) == len(occurred_at)

    tracker = ObstacleTracker(smoothing_alpha=1.0)
    detections = [
        Detection("Car", (float(offset), 0.0, 20.0 + offset, 20.0), distance_m=distance)
        for offset, distance in enumerate((40.0, 39.0, 38.0))
    ]
    for detection, timestamp_s in zip(detections, timestamps, strict=True):
        tracker.update([detection], timestamp_s=timestamp_s)

    assert {detection.track_id for detection in detections} == {detections[0].track_id}
    assert detections[-1].relative_speed_mps == pytest.approx(10.0)
    assert detections[-1].ttc_s == pytest.approx(3.8)


def test_real_timestamp_takes_precedence_over_processing_fallback() -> None:
    assert (
        pipeline._timestamp_s({"timestamp": 42.5}, processing_index=99, fps=10.0)
        == 42.5
    )
