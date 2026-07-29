FROM ghcr.io/astral-sh/uv:0.11.11-python3.12-bookworm-slim AS builder

WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY packages/observability packages/observability
COPY apps/api apps/api

RUN uv sync --frozen --no-dev --package fleetiq-api --no-editable

FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="FleetIQ API"

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 fleetiq
USER fleetiq

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD \
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"

CMD ["uvicorn", "fleetiq_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
