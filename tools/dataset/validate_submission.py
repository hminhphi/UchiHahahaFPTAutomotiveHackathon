"""Validate organizer-format prediction CSVs against the local scored trips."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from pathlib import Path

from export_submission import ACCEPTED_DRIVER_STATES, SUBMISSION_COLUMNS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-dir", type=Path, required=True)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted"),
    )
    return parser.parse_args()


def trip_frame_ids(path: Path) -> list[int]:
    document_path = path / f"{path.name}.json.gz"
    document = json.loads(gzip.decompress(document_path.read_bytes()))
    frames = document.get("frames", [])
    return [int(frame.get("frame_id", index)) for index, frame in enumerate(frames)]


def validate_csv(path: Path, expected_ids: list[int]) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SUBMISSION_COLUMNS:
            raise ValueError(f"{path.name}: invalid header {reader.fieldnames}")
        rows = list(reader)
    ids = [int(row["frame_id"]) for row in rows]
    if ids != expected_ids:
        raise ValueError(
            f"{path.name}: frame IDs do not match dataset "
            f"(expected {len(expected_ids)}, received {len(ids)})"
        )

    finite_ttc = 0
    for row in rows:
        ttc = float(row["predicted_ttc"])
        if math.isfinite(ttc):
            if ttc < 0:
                raise ValueError(f"{path.name}: negative TTC at frame {row['frame_id']}")
            finite_ttc += 1
        if row["predicted_driver_state"] not in ACCEPTED_DRIVER_STATES:
            raise ValueError(f"{path.name}: invalid driver state at frame {row['frame_id']}")
        risk = float(row["predicted_risk_score"])
        if not math.isfinite(risk) or not 0 <= risk <= 100:
            raise ValueError(f"{path.name}: invalid risk score at frame {row['frame_id']}")
    return {"frames": len(rows), "finite_ttc": finite_ttc}


def main() -> int:
    args = parse_args()
    trips = sorted(
        path for path in args.dataset_root.iterdir() if path.is_dir() and path.name.endswith("d")
    )
    failures: list[str] = []
    for trip in trips:
        csv_path = args.predictions_dir / f"{trip.name}.csv"
        try:
            result = validate_csv(csv_path, trip_frame_ids(trip))
            print(f"[OK] {trip.name}: {result['frames']} frames, {result['finite_ttc']} finite TTC")
        except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as error:
            failures.append(f"[ERROR] {trip.name}: {error}")
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
