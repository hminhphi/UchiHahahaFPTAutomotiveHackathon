from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fleetiq_training_roadface.prepare_dataset import main as prepare_main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train or fine-tune road-facing detector models from projected KITTI labels."
    )
    parser.add_argument(
        "--dataset-yaml",
        type=Path,
        default=Path("artifacts/training/roadface/yolo_dataset/dataset.yaml"),
    )
    parser.add_argument("--prepare", action="store_true", help="Export the YOLO dataset before training.")
    parser.add_argument("--model", default="yolo11l.pt", help="Ultralytics model/checkpoint.")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=768)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cache", choices=("false", "ram", "disk"), default="false")
    parser.add_argument("--amp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--close-mosaic", type=int, default=10)
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("artifacts/training/roadface/train_runs"),
    )
    parser.add_argument("--name", default="yolo_roadface")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the exact training plan without importing Ultralytics.",
    )
    return parser.parse_args()


def write_plan(args: argparse.Namespace) -> Path:
    plan = {
        "detector": {
            "framework": "ultralytics",
            "model": args.model,
            "dataset_yaml": str(args.dataset_yaml.resolve()),
            "epochs": args.epochs,
            "imgsz": args.imgsz,
            "batch": args.batch,
            "device": args.device,
            "workers": args.workers,
            "cache": args.cache,
            "amp": args.amp,
            "fraction": args.fraction,
            "patience": args.patience,
            "close_mosaic": args.close_mosaic,
            "output_project": str(args.project.resolve()),
            "run_name": args.name,
        },
        "depth_models_to_compare": [
            "gt",
            "stereo",
            "transformers:depth-anything/Depth-Anything-V2-Metric-Outdoor-Large-hf",
            "transformers:Intel/zoedepth-nyu-kitti",
        ],
        "notes": [
            "The detector is trained from projected 3D KITTI boxes in practice trips.",
            "For redacted trips, labels cannot be used for detection because 2D/3D label fields are zeroed.",
            "Depth models are evaluated through fleetiq-roadface and fleetiq-evaluate-roadface.",
        ],
    }
    args.project.mkdir(parents=True, exist_ok=True)
    path = args.project / f"{args.name}_training_plan.json"
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    if args.prepare:
        old_argv = sys.argv[:]
        try:
            sys.argv = ["fleetiq-prepare-roadface"]
            prepare_main()
        finally:
            sys.argv = old_argv
    plan_path = write_plan(args)
    if args.dry_run:
        print(f"Wrote dry-run plan: {plan_path}")
        return
    if not args.dataset_yaml.exists():
        raise SystemExit(
            f"Dataset yaml not found: {args.dataset_yaml}. Run with --prepare first."
        )
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Ultralytics is not installed. Run: uv sync --all-packages --extra models"
        ) from exc
    model = YOLO(args.model)
    train_kwargs = {
        "data": str(args.dataset_yaml.resolve()),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "cache": False if args.cache == "false" else args.cache,
        "amp": args.amp,
        "fraction": args.fraction,
        "patience": args.patience,
        "close_mosaic": args.close_mosaic,
        "project": str(args.project.resolve()),
        "name": args.name,
        "exist_ok": True,
    }
    if args.device is not None:
        train_kwargs["device"] = args.device
    results = model.train(**train_kwargs)
    print(f"Training complete: {results}")
    print(f"Plan: {plan_path}")


if __name__ == "__main__":
    main()
