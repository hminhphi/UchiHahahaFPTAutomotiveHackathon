"""Run the optional YOLO phone-use signal for one saved trip."""

import argparse
from pathlib import Path

import pandas as pd

from fleetiq_training_dms.phone_detector import PhoneUseDetector, PhoneUseSmoother


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect phone use in saved driver-camera frames")
    parser.add_argument("--trip-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("yolo11n.pt"))
    parser.add_argument("--confidence", type=float, default=0.40)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    frames = sorted((args.trip_dir / "driver").glob("frame_*.jpg"))
    if not frames:
        raise SystemExit(f"No driver frames found under {args.trip_dir / 'driver'}")
    if not args.model.is_file():
        raise SystemExit(
            f"Model not found: {args.model}\n"
            "Prepare it with: uv run --with ultralytics python -c "
            "'from ultralytics import YOLO; YOLO(\"yolo11n.pt\")'"
        )

    detector = PhoneUseDetector(args.model, confidence=args.confidence)
    smoother = PhoneUseSmoother()
    rows = []
    for image_path in frames:
        frame_id = int(image_path.stem.rsplit("_", 1)[-1])
        rows.append({
            "frame_id": frame_id,
            "phone_use": smoother.update(detector.detect(image_path)),
        })

    output = args.output or Path("artifacts/predictions/dms") / f"{args.trip_dir.name}_twostage.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    phone = pd.DataFrame(rows)
    if output.is_file():
        existing = pd.read_csv(output).drop(columns=["phone_use"], errors="ignore")
        phone = existing.merge(phone, on="frame_id", how="left")
    phone.to_csv(output, index=False)
    print(f"Saved {len(phone):,} frame results to {output}")
    print(f"Detected: {int(phone.phone_use.eq(True).sum()):,}")


if __name__ == "__main__":
    main()
