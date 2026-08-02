import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_python_dockerfiles_copy_pinned_uv_binary_from_distroless_image() -> None:
    dockerfiles = [
        Path(relative)
        for relative in subprocess.check_output(
            ["git", "ls-files", "*Dockerfile"],
            cwd=ROOT,
            text=True,
        ).splitlines()
    ]
    offenders = []
    for relative in dockerfiles:
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "uv sync" not in text:
            continue
        if "FROM ghcr.io/astral-sh/uv:" in text:
            offenders.append(str(relative).replace("\\", "/"))
        assert "COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/" in text

    assert offenders == []


def test_api_runtime_declares_websocket_transport_for_uvicorn() -> None:
    pyproject = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text(encoding="utf-8"))
    dependencies = tuple(pyproject["project"]["dependencies"])

    assert any(
        dependency.startswith("websockets") or dependency.startswith("uvicorn[standard]")
        for dependency in dependencies
    )


def test_local_mqtt_broker_is_on_edge_network_for_host_smoke_tests() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    mosquitto_block = compose.split("  mosquitto:", 1)[1].split("\n  api:", 1)[0]

    assert "ports:" in mosquitto_block
    assert "networks: [edge, backend]" in mosquitto_block
