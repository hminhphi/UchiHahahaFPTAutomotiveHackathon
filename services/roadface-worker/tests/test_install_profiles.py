from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = REPOSITORY_ROOT / "packages" / "contracts"
DATA_KIT = REPOSITORY_ROOT / "packages" / "data-kit"
ROADFACE = REPOSITORY_ROOT / "services" / "roadface-worker"
TRAINING = REPOSITORY_ROOT / "ml" / "training" / "roadface"


def uv_executable() -> str:
    executable = os.environ.get("FLEETIQ_TEST_UV") or shutil.which("uv")
    if executable is None:
        pytest.skip("Set FLEETIQ_TEST_UV or install uv to run package-profile tests.")
    return executable


def environment_python(environment: Path) -> Path:
    if sys.platform == "win32":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def create_installed_environment(
    tmp_path: Path,
    name: str,
    requirements: list[str],
) -> Path:
    environment = tmp_path / name
    uv = uv_executable()
    subprocess.run(
        [uv, "venv", "--python", sys.executable, str(environment)],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    python = environment_python(environment)
    completed = subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--python",
            str(python),
            "--strict",
            *requirements,
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return python


def run_profile_smoke(python: Path, source: str) -> None:
    completed = subprocess.run(
        [str(python), "-c", textwrap.dedent(source)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def local_requirements(*packages: Path) -> list[str]:
    return [str(CONTRACTS), str(DATA_KIT), *(str(package) for package in packages)]


def test_default_roadface_noneditable_import_without_opencv(tmp_path: Path) -> None:
    python = create_installed_environment(
        tmp_path,
        "roadface-default",
        local_requirements(ROADFACE),
    )

    run_profile_smoke(
        python,
        """
        import importlib.metadata
        import subprocess
        import sys

        import fleetiq_roadface

        installed = {
            dist.metadata["Name"].lower()
            for dist in importlib.metadata.distributions()
            if dist.metadata["Name"]
        }
        direct_url = importlib.metadata.distribution(
            "fleetiq-roadface"
        ).read_text("direct_url.json")

        assert "opencv-python" not in installed
        assert "opencv-python-headless" not in installed
        assert "cv2" not in sys.modules
        assert '"editable": true' not in (direct_url or "").lower()

        help_result = subprocess.run(
            [sys.executable, "-m", "fleetiq_roadface.cli", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert help_result.returncode == 0, help_result.stderr

        try:
            fleetiq_roadface.RoadfacePipeline
        except RuntimeError as exc:
            assert "fleetiq-roadface[headless]" in str(exc)
        else:
            raise AssertionError("Pipeline loaded without an OpenCV runtime")
        """,
    )


def test_headless_roadface_noneditable_runtime_import(tmp_path: Path) -> None:
    python = create_installed_environment(
        tmp_path,
        "roadface-headless",
        local_requirements(Path(f"{ROADFACE}[headless]")),
    )

    run_profile_smoke(
        python,
        """
        import importlib.metadata

        import fleetiq_roadface
        from fleetiq_roadface import PipelineOptions, RoadfacePipeline

        installed = {
            dist.metadata["Name"].lower()
            for dist in importlib.metadata.distributions()
            if dist.metadata["Name"]
        }
        direct_url = importlib.metadata.distribution(
            "fleetiq-roadface"
        ).read_text("direct_url.json")

        assert RoadfacePipeline.__name__ == "RoadfacePipeline"
        assert PipelineOptions.__name__ == "PipelineOptions"
        assert "opencv-python-headless" in installed
        assert "opencv-python" not in installed
        assert '"editable": true' not in (direct_url or "").lower()
        """,
    )


def test_training_gui_noneditable_runtime_has_no_opencv_conflict(
    tmp_path: Path,
) -> None:
    python = create_installed_environment(
        tmp_path,
        "training-gui",
        local_requirements(ROADFACE, TRAINING),
    )

    run_profile_smoke(
        python,
        """
        import importlib.metadata
        import re

        import cv2
        import fleetiq_training_roadface.experimental
        from fleetiq_roadface import RoadfacePipeline

        installed = {
            dist.metadata["Name"].lower()
            for dist in importlib.metadata.distributions()
            if dist.metadata["Name"]
        }
        direct_url = importlib.metadata.distribution(
            "fleetiq-training-roadface"
        ).read_text("direct_url.json")
        gui = re.search(
            r"^\\s*GUI:\\s+(\\S+)",
            cv2.getBuildInformation(),
            re.MULTILINE,
        )

        assert RoadfacePipeline.__name__ == "RoadfacePipeline"
        assert "opencv-python" in installed
        assert "opencv-python-headless" not in installed
        assert callable(cv2.namedWindow)
        assert gui is not None and gui.group(1).upper() != "NONE"
        assert '"editable": true' not in (direct_url or "").lower()
        """,
    )
