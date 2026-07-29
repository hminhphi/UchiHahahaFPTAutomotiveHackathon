# Generic build template for a Python workspace package.
# Build with --build-arg PACKAGE=<uv-package> --build-arg ENTRYPOINT=<console-script>.
FROM ghcr.io/astral-sh/uv:0.11.11-python3.12-bookworm-slim AS builder

ARG PACKAGE
WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
COPY packages packages
COPY services services
COPY apps apps
RUN test -n "${PACKAGE}" \
    && uv sync --frozen --no-dev --package "${PACKAGE}" --no-editable

FROM python:3.12-slim-bookworm

ARG ENTRYPOINT
LABEL org.opencontainers.image.title="FleetIQ Python service template"
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    SERVICE_ENTRYPOINT="${ENTRYPOINT}"

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
RUN test -n "${ENTRYPOINT}" \
    && useradd --create-home --uid 10001 fleetiq
USER fleetiq

ENTRYPOINT ["sh", "-c", "exec \"$SERVICE_ENTRYPOINT\" \"$@\"", "--"]
