FROM ghcr.io/astral-sh/uv:0.11.11-python3.12-bookworm-slim AS builder

WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY packages/model-clients packages/model-clients
COPY services/dms-worker services/dms-worker

RUN uv sync --frozen --no-dev --package fleetiq-dms-worker --no-editable

FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="FleetIQ DMS worker"

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 fleetiq
USER fleetiq

ENTRYPOINT ["fleetiq-dms-worker"]
