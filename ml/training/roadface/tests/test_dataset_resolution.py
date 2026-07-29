from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fleetiq_training_roadface.datasets import (
    dataset_roots,
    discover_trip_dirs,
)
from fleetiq_training_roadface.experimental import discover_trips


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def create_trip(dataset_root: Path, trip_id: str = "T99-Sample") -> Path:
    trip_dir = dataset_root / trip_id
    image_dir = trip_dir / "kitti" / "image_2"
    image_dir.mkdir(parents=True)
    (image_dir / "000000.png").write_bytes(b"manifest-only does not decode images")
    with gzip.open(trip_dir / f"{trip_id}.json.gz", "wt", encoding="utf-8") as handle:
        json.dump({"frames": []}, handle)
    return trip_dir


def test_named_dataset_uses_environment_root_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_root = tmp_path / "external-dataset"
    trip_dir = create_trip(dataset_root)
    outside = tmp_path / "unrelated-working-directory"
    outside.mkdir()
    monkeypatch.setenv("FLEETIQ_DATA_ROOT", str(dataset_root))
    monkeypatch.chdir(outside)

    assert dataset_roots("practice") == (dataset_root.resolve(),)
    assert discover_trip_dirs("practice") == [trip_dir.resolve()]
    assert discover_trips("practice") == [trip_dir.resolve()]


def test_repository_fallback_is_independent_of_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "unrelated-working-directory"
    outside.mkdir()
    monkeypatch.delenv("FLEETIQ_DATA_ROOT", raising=False)
    monkeypatch.chdir(outside)

    assert dataset_roots("practice") == (
        (
            REPOSITORY_ROOT
            / "data"
            / "Practice_Dataset"
            / "Practice_Dataset"
        ).resolve(),
    )


def test_explicit_dataset_root_wins_over_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment_root = tmp_path / "environment"
    explicit_root = tmp_path / "explicit"
    create_trip(environment_root, "T98-Sample")
    explicit_trip = create_trip(explicit_root, "T97-Sample")
    monkeypatch.setenv("FLEETIQ_DATA_ROOT", str(environment_root))

    assert dataset_roots(explicit_root) == (explicit_root.resolve(),)
    assert discover_trip_dirs(explicit_root) == [explicit_trip.resolve()]


def test_manifest_only_honors_environment_from_outside_repo(tmp_path: Path) -> None:
    dataset_root = tmp_path / "external-dataset"
    create_trip(dataset_root)
    outside = tmp_path / "unrelated-working-directory"
    outside.mkdir()
    environment = os.environ.copy()
    environment["FLEETIQ_DATA_ROOT"] = str(dataset_root)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fleetiq_training_roadface.label_locateanything",
            "--dataset",
            "practice",
            "--manifest-only",
        ],
        cwd=outside,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Selected 1 trips, 1 image_2 frames" in completed.stdout
    assert "T99-Sample: 1" in completed.stdout
