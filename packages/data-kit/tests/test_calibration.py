from __future__ import annotations

from pathlib import Path

import pytest
from fleetiq_data.calibration import parse_calibration


def test_parse_stereo_projection_and_baseline(tmp_path: Path) -> None:
    calib = tmp_path / "000000.txt"
    calib.write_text(
        "P2: 700 0 320 0 0 700 180 0 0 0 1 0\n"
        "P3: 700 0 320 -210 0 700 180 0 0 0 1 0\n",
        encoding="utf-8",
    )

    parsed = parse_calibration(calib)

    assert parsed.baseline_m == 0.3
    assert parsed.fx == 700.0
    assert parsed.projections["P2"].shape == (3, 4)


def test_parse_stereo_projection_with_translated_left_camera(tmp_path: Path) -> None:
    calib = tmp_path / "000000.txt"
    calib.write_text(
        "P2: 700 0 320 -70 0 700 180 0 0 0 1 0\n"
        "P3: 700 0 320 -280 0 700 180 0 0 0 1 0\n",
        encoding="utf-8",
    )

    parsed = parse_calibration(calib)

    assert parsed.baseline_m == pytest.approx(0.3)


def test_parse_calibration_rejects_missing_stereo_projection(tmp_path: Path) -> None:
    calib = tmp_path / "000000.txt"
    calib.write_text("P2: 700 0 320 0 0 700 180 0 0 0 1 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="P3"):
        parse_calibration(calib)
