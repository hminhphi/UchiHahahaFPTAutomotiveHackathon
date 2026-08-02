FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/
WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY services/coaching-worker services/coaching-worker
RUN uv sync --frozen --no-dev --package fleetiq-coaching-worker --no-editable

FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.title="FleetIQ coaching worker"
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 fleetiq
USER fleetiq
ENTRYPOINT ["fleetiq-coaching-worker"]
