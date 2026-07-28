"""KITTI calibration parsing and stereo camera geometry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class Calibration:
    """Parsed KITTI calibration values anchored on the left P2 camera."""

    values: dict[str, np.ndarray]
    projections: dict[str, np.ndarray]
    fx: float
    fy: float
    cx: float
    cy: float
    baseline_m: float

    def projection(self, name: str) -> np.ndarray:
        """Return a named projection matrix."""
        return self.projections[name]


def parse_calibration(path: Path) -> Calibration:
    """Parse a KITTI calibration file without changing its field layout."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Calibration file not found: {path}")

    values: dict[str, np.ndarray] = {}
    projections: dict[str, np.ndarray] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key, separator, raw_values = raw_line.partition(":")
        if not separator:
            continue
        numbers = np.fromstring(raw_values, sep=" ", dtype=np.float64)
        if numbers.size == 0:
            continue
        matrix = _reshape_calibration_value(key, numbers)
        values[key] = matrix
        if key.startswith("P") and matrix.shape == (3, 4):
            projections[key] = matrix

    p2 = projections.get("P2")
    p3 = projections.get("P3")
    if p2 is None:
        raise ValueError(f"Calibration {path} does not contain a P2 projection")
    if p3 is None:
        raise ValueError(f"Calibration {path} does not contain a P3 projection")
    if np.isclose(p2[0, 0], 0.0) or np.isclose(p3[0, 0], 0.0):
        raise ValueError(f"Calibration {path} has a zero stereo focal length")

    return Calibration(
        values=values,
        projections=projections,
        fx=float(p2[0, 0]),
        fy=float(p2[1, 1]),
        cx=float(p2[0, 2]),
        cy=float(p2[1, 2]),
        baseline_m=_stereo_baseline(p2, p3),
    )


def _reshape_calibration_value(key: str, numbers: np.ndarray) -> np.ndarray:
    if key.startswith("P") and numbers.size == 12:
        return numbers.reshape(3, 4)
    if key == "R0_rect" and numbers.size == 9:
        return numbers.reshape(3, 3)
    if numbers.size == 12:
        return numbers.reshape(3, 4)
    return numbers


def _stereo_baseline(p2: np.ndarray, p3: np.ndarray) -> float:
    """Return stereo baseline, preserving the standard KITTI formula exactly."""
    if np.allclose(p2[:, 3], 0.0):
        return float(-p3[0, 3] / p3[0, 0])

    p2_center = _camera_center(p2)
    p3_center = _camera_center(p3)
    return float(np.linalg.norm(p3_center - p2_center))


def _camera_center(projection: np.ndarray) -> np.ndarray:
    camera_matrix = projection[:, :3]
    translation = projection[:, 3]
    if np.linalg.matrix_rank(camera_matrix) != 3:
        raise ValueError("Stereo projection has a singular camera matrix")
    return -np.linalg.solve(camera_matrix, translation)
