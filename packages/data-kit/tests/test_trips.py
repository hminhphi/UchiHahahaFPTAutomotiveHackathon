from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fleetiq_data.paths import DatasetPaths
from fleetiq_data.telemetry import normalize_telemetry
from fleetiq_data.trips import discover_trips, load_trip_document, resolve_trip


def test_discover_trips_uses_explicit_root(tmp_path: Path) -> None:
    trip = tmp_path / "T01-Sample"
    trip.mkdir()
    with gzip.open(trip / "T01-Sample.json.gz", "wt", encoding="utf-8") as handle:
        json.dump({"frames": []}, handle)

    assert [item.trip_id for item in discover_trips(tmp_path)] == ["T01-Sample"]


def test_resolve_and_load_trip_document_case_insensitively(tmp_path: Path) -> None:
    trip = tmp_path / "T01-Sample"
    trip.mkdir()
    with gzip.open(trip / "T01-Sample.json.gz", "wt", encoding="utf-8") as handle:
        json.dump({"frames": [{"speed": 10}]}, handle)

    record = resolve_trip(tmp_path, "t01-sample")

    assert record.trip_dir == trip
    assert load_trip_document(record) == {"frames": [{"speed": 10}]}


def test_dataset_paths_reads_environment_only_on_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLEETIQ_DATA_ROOT", str(tmp_path))

    paths = DatasetPaths.from_env()

    assert paths.root == tmp_path


def test_normalize_telemetry_keeps_frame_order_and_finite_numbers() -> None:
    frames = [
        {"speed": "12.5", "driver": {"state": "attentive"}},
        {"speed": "Infinity", "driver": {"state": "distracted"}},
    ]

    telemetry = normalize_telemetry(frames)

    assert [item.frame_id for item in telemetry] == [0, 1]
    assert telemetry[0].speed_mps == 12.5
    assert telemetry[1].speed_mps is None
    assert telemetry[1].driver_state == "distracted"


def test_normalize_telemetry_preserves_zero_values_over_legacy_fallbacks() -> None:
    telemetry = normalize_telemetry(
        [
            {
                "speed": 12.5,
                "ego": {
                    "speed_mps": 0.0,
                    "speed_kmh": 36.0,
                    "longitudinal_accel": 0.0,
                    "lateral_accel": 0.0,
                },
            }
        ]
    )

    assert telemetry[0].speed_mps == 0.0
    assert telemetry[0].longitudinal_accel_mps2 == 0.0
    assert telemetry[0].lateral_accel_mps2 == 0.0


def test_trip_cli_does_not_preimport_its_module(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fleetiq_data.trips",
            "--root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "RuntimeWarning" not in completed.stderr
