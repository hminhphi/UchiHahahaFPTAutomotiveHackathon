"""Batch pipeline: run YOLOv26 + tracking + depth + TTC on all detached Hackathon trips."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fleetiq_data import DatasetPaths
from fleetiq_roadface.pipeline import PipelineOptions, RoadfacePipeline
from fleetiq_roadface.yolo_detector import YoloDetector


def main() -> None:
    dataset_root = Path("data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted")
    if not dataset_root.is_dir():
        print(f"Dataset not found: {dataset_root}", file=sys.stderr)
        sys.exit(1)

    dataset = DatasetPaths(dataset_root)
    output_root = Path("artifacts/predictions/roadface/hackathon_yolo26n")
    pipeline = RoadfacePipeline(
        dataset_paths=dataset,
        output_root=output_root,
        detector=YoloDetector(
            model_path=Path(
                "artifacts/training/roadface/train_runs/"
                "yolo26n_detached_v3/weights/best.pt"
            ),
            device="cuda:0",
            confidence_threshold=0.25,
        ),
        depth_model=None,
    )

    options = PipelineOptions(
        detector_source="model",
        depth_source="gt",
        lane_method="classical",
        lane_filter=False,
        visualize=False,
    )

    trip_ids = sorted(
        d.name for d in dataset_root.iterdir()
        if d.is_dir() and d.name.startswith("T") and d.name.endswith("d")
    )

    for trip_id in trip_ids:
        print(f"\n{'='*60}")
        print(f"Processing: {trip_id}")
        try:
            trip = pipeline.resolve_trip(trip_id)
            results = pipeline.run_trip(trip, start=0, end=None, stride=1, options=options)
            print(f"  Frames: {len(results)}")

            if results:
                first = json.loads(results[0].read_text())
                dets = first.get("detections", [])
                print(f"  Frame 0 detections: {len(dets)}")
                for d in dets[:3]:
                    print(f"    track={d.get('track_id','?')} | {d['label']:15s} | dist={d.get('distance_m','?')} | ttc={d.get('ttc_s','?')}")

        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)

    print(f"\nDone. Output: {output_root}")


if __name__ == "__main__":
    main()
