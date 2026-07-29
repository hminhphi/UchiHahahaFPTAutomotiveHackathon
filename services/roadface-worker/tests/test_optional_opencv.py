from __future__ import annotations

import subprocess
import sys
import textwrap


def run_isolated_python(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_public_package_import_does_not_import_opencv() -> None:
    completed = run_isolated_python(
        """
        import sys
        import fleetiq_roadface

        assert "cv2" not in sys.modules
        assert fleetiq_roadface.Detection.__name__ == "Detection"
        """
    )

    assert completed.returncode == 0, completed.stderr

def test_pipeline_access_reports_the_optional_runtime_dependency() -> None:
    completed = run_isolated_python(
        """
        import importlib.abc
        import sys

        class BlockOpenCV(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path, target=None):
                if fullname == "cv2":
                    raise ModuleNotFoundError("No module named 'cv2'", name="cv2")
                return None

        sys.meta_path.insert(0, BlockOpenCV())
        import fleetiq_roadface

        try:
            fleetiq_roadface.RoadfacePipeline
        except RuntimeError as exc:
            message = str(exc)
            assert "fleetiq-roadface[headless]" in message
            assert "opencv-python" in message
        else:
            raise AssertionError("RoadfacePipeline unexpectedly loaded without OpenCV")
        """
    )

    assert completed.returncode == 0, completed.stderr


def test_cli_help_does_not_require_opencv() -> None:
    completed = run_isolated_python(
        """
        import importlib.abc
        import runpy
        import sys

        class BlockOpenCV(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path, target=None):
                if fullname == "cv2":
                    raise ModuleNotFoundError("No module named 'cv2'", name="cv2")
                return None

        sys.meta_path.insert(0, BlockOpenCV())
        sys.argv = ["fleetiq-roadface", "--help"]

        try:
            runpy.run_module("fleetiq_roadface.cli", run_name="__main__")
        except SystemExit as exc:
            assert exc.code == 0
        """
    )

    assert completed.returncode == 0, completed.stderr
