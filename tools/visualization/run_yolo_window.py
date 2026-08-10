"""
Run full YOLO pipeline on a trip and display results in a window.

Usage:
    uv run python tools/visualization/run_yolo_window.py --trip T01d
    uv run python tools/visualization/run_yolo_window.py --trip T01d --fps 10
    uv run python tools/visualization/run_yolo_window.py --trip T01d --conf 0.3 --start 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "services/roadface-worker/src"))

from fleetiq_data import DatasetPaths, resolve_trip
from fleetiq_roadface.pipeline import PipelineOptions, RoadfacePipeline
from fleetiq_roadface.rendering import draw_overlay
from fleetiq_roadface.yolo_detector import YoloDetector


DATASET_ROOT = ROOT / "data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YOLO pipeline and display in window")
    parser.add_argument("--trip", required=True, help="Trip ID, e.g. T01d")
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--conf", type=float, default=0.25, help="YOLO confidence threshold")
    parser.add_argument("--device", default="cuda:0", help="CUDA device or cpu")
    parser.add_argument(
        "--model",
        type=Path,
        default=(
            ROOT
            / "artifacts/training/roadface/train_runs"
            / "yolo26n_detached_v3/weights/best.pt"
        ),
    )
    parser.add_argument("--no-lane", action="store_true", help="Disable lane detection")
    parser.add_argument("--depth-source", choices=("gt", "stereo", "none"), default="gt")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not DATASET_ROOT.is_dir():
        print(f"Dataset not found: {DATASET_ROOT}")
        sys.exit(1)

    if not args.model.exists():
        print(f"Model not found: {args.model}")
        print("Expected: artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt")
        sys.exit(1)

    print(f"Loading YOLO model from: {args.model}")
    detector = YoloDetector(
        model_path=args.model,
        device=args.device,
        confidence_threshold=args.conf,
    )

    dataset = DatasetPaths(DATASET_ROOT)
    trip = resolve_trip(dataset, args.trip)

    pipeline = RoadfacePipeline(
        dataset_paths=dataset,
        output_root=ROOT / "artifacts/predictions/roadface/yolo_window",
        detector=detector,
        depth_model=None,
    )

    options = PipelineOptions(
        detector_source="model",
        depth_source=args.depth_source,
        lane_method="classical",
        lane_filter=not args.no_lane,
        visualize=False,  # we render manually for window display
    )

    # Load trip frames to iterate
    from fleetiq_data import load_trip_document, find_frame
    doc = load_trip_document(trip)
    raw_frames = doc.get("frames", [])

    print(f"Trip: {args.trip} | Frames: {len(raw_frames)} | FPS: {args.fps}")
    print("Press Q or ESC to quit, SPACE to pause")
    print()

    delay_ms = max(1, int(1000 / args.fps))
    paused = False
    frame_count = 0

    cv2.namedWindow(f"FleetIQ YOLO - {args.trip}", cv2.WINDOW_NORMAL)
    cv2.resizeWindow(f"FleetIQ YOLO - {args.trip}", 1280, 400)

    for list_index, frame_data in enumerate(raw_frames):
        frame_index = frame_data.get("frame_id", list_index)

        if frame_index < args.start:
            continue
        if args.end is not None and frame_index > args.end:
            break
        if (frame_index - args.start) % max(1, args.stride) != 0:
            continue

        # Load image
        img_path = find_frame(trip.image_2_dir, frame_index)
        if img_path is None:
            continue
        import cv2 as _cv2
        image = _cv2.imread(str(img_path))
        if image is None:
            continue

        # Run YOLO
        detections = detector(image)

        # Load lane
        from fleetiq_roadface.lane import estimate_classical_lane
        lane = estimate_classical_lane(image) if not args.no_lane else None

        # Render
        overlay = draw_overlay(image, detections, lane)

        # Add frame info HUD
        ego = frame_data.get("ego", {})
        speed = ego.get("speed_kmh", 0)
        det_str = f"dets={len(detections)}"
        info = f"Trip:{args.trip}  Frame:{frame_index:05d}  Speed:{speed:.0f}km/h  {det_str}"
        cv2.rectangle(overlay, (0, 0), (len(info) * 9 + 10, 26), (15, 20, 30), -1)
        cv2.putText(overlay, info, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 220), 1, cv2.LINE_AA)

        cv2.imshow(f"FleetIQ YOLO - {args.trip}", overlay)

        frame_count += 1
        if frame_count % 50 == 0:
            print(f"  Frame {frame_index:05d} | speed={speed:.0f} km/h | detections={len(detections)}")

        while True:
            key = cv2.waitKey(0 if paused else delay_ms) & 0xFF
            if key in (27, ord("q")):  # ESC or Q
                cv2.destroyAllWindows()
                print(f"\nDone. Processed {frame_count} frames.")
                return
            elif key == ord(" "):  # SPACE toggle pause
                paused = not paused
                if not paused:
                    break
            else:
                break

    cv2.destroyAllWindows()
    print(f"\nDone. Processed {frame_count} frames.")


if __name__ == "__main__":
    main()
