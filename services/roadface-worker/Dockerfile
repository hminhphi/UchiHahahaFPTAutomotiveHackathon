FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/

WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY packages/data-kit packages/data-kit
COPY services/roadface-worker services/roadface-worker

RUN uv sync --frozen --no-dev --package fleetiq-roadface --extra headless --no-editable

FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="FleetIQ roadface worker"

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 fleetiq
USER fleetiq

ENTRYPOINT ["fleetiq-roadface"]
