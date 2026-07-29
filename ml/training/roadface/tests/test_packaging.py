from __future__ import annotations

import importlib.metadata
import re
import tomllib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
TRAINING_PYPROJECT = REPOSITORY_ROOT / "ml" / "training" / "roadface" / "pyproject.toml"
RUNTIME_PYPROJECT = REPOSITORY_ROOT / "services" / "roadface-worker" / "pyproject.toml"


def dependency_name(requirement: str) -> str:
    return re.split(r"[\s<>=!~;\[]", requirement, maxsplit=1)[0].lower()


def project_metadata(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))["project"]


def test_training_default_has_one_gui_opencv_provider_and_gif_support() -> None:
    metadata = project_metadata(TRAINING_PYPROJECT)
    dependencies = {dependency_name(item) for item in metadata["dependencies"]}

    assert "opencv-python" in dependencies
    assert "opencv-python-headless" not in dependencies
    assert "imageio" in dependencies


def test_runtime_headless_opencv_is_isolated_in_one_extra() -> None:
    metadata = project_metadata(RUNTIME_PYPROJECT)
    default_dependencies = {
        dependency_name(item) for item in metadata["dependencies"]
    }
    headless_dependencies = {
        dependency_name(item)
        for item in metadata["optional-dependencies"]["headless"]
    }

    assert "opencv-python" not in default_dependencies
    assert "opencv-python-headless" not in default_dependencies
    assert headless_dependencies == {"opencv-python-headless"}


def test_worker_container_selects_the_headless_extra() -> None:
    dockerfile = (
        REPOSITORY_ROOT / "services" / "roadface-worker" / "Dockerfile"
    ).read_text(encoding="utf-8")

    assert "uv sync --frozen --no-dev --package fleetiq-roadface --extra headless" in dockerfile


def test_installed_gui_profile_has_highgui_without_headless_conflict() -> None:
    installed = {
        distribution.metadata["Name"].lower()
        for distribution in importlib.metadata.distributions()
        if distribution.metadata["Name"]
    }

    assert "opencv-python" in installed
    assert "opencv-python-headless" not in installed

    import cv2

    assert callable(cv2.namedWindow)
    match = re.search(r"^\s*GUI:\s+(\S+)", cv2.getBuildInformation(), re.MULTILINE)
    assert match is not None
    assert match.group(1).upper() != "NONE"


def test_every_gif_code_path_is_covered_by_training_metadata() -> None:
    metadata = project_metadata(TRAINING_PYPROJECT)
    dependencies = {dependency_name(item) for item in metadata["dependencies"]}
    gif_sources = [
        REPOSITORY_ROOT
        / "ml"
        / "training"
        / "roadface"
        / "src"
        / "fleetiq_training_roadface"
        / "panoptic_labels.py",
        REPOSITORY_ROOT
        / "tools"
        / "visualization"
        / "roadface"
        / "visualize_yolop_lane_offset.py",
    ]

    assert all("import imageio" in path.read_text(encoding="utf-8") for path in gif_sources)
    assert "imageio" in dependencies
