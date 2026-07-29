FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="FleetIQ local SageMaker mock"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_MOCK_PORT=8080

WORKDIR /app
COPY infra/docker/model-mock/app.py /app/app.py

RUN useradd --create-home --uid 10001 fleetiq
USER fleetiq

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD \
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/ping', timeout=2)"

CMD ["python", "/app/app.py"]
