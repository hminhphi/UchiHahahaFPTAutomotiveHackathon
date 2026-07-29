FROM python:3.12-slim

LABEL org.opencontainers.image.title="FleetIQ CarSky bridge"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BRIDGE_PORT=8090

WORKDIR /app
COPY bridge.py /app/bridge.py

RUN useradd --create-home --uid 10001 fleetiq
USER fleetiq

EXPOSE 8090
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD \
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2)"

CMD ["python", "/app/bridge.py"]
