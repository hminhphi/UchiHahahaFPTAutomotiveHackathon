from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fleetiq_contracts import InferenceResponse
from fleetiq_data import DatasetPaths
from fleetiq_roadface.pipeline import RoadfacePipeline
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
