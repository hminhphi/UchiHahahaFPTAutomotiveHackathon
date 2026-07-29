from pathlib import Path

DOCKERFILE = Path(__file__).parents[1] / "Dockerfile"


def test_runtime_uses_non_editable_path_stable_environment() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "UV_PROJECT_ENVIRONMENT=/opt/venv" in dockerfile
    assert (
        "uv sync --frozen --no-dev --package fleetiq-roadface "
        "--extra headless --no-editable"
        in dockerfile
    )
    assert "COPY --from=builder /opt/venv /opt/venv" in dockerfile
    assert 'PATH="/opt/venv/bin:$PATH"' in dockerfile
    assert "COPY --from=builder /workspace/.venv" not in dockerfile
    runtime_stage = dockerfile.split("FROM python:3.12-slim-bookworm AS runtime", 1)[1]
    assert "/workspace" not in runtime_stage
