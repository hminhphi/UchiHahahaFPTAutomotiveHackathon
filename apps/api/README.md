# FleetIQ API

The API is the HTTP and WebSocket control plane owned by the backend team. It
handles trip queries, idempotent analysis jobs, camera ingress, and latest live
trip state. Long-running inference belongs in workers and SageMaker; camera
bytes never use MQTT.

## Interfaces

- HTTP: `/health/live`, `/health/ready`, `/api/v1/trips`, `/api/v1/jobs`
- Camera WebSocket: `/ws/v1/trips/{trip_id}/camera/{view}`
- Live-state WebSocket: `/ws/v1/trips/{trip_id}/live`
- Inputs: versioned JSON requests and binary JPEG frame packets
- Outputs: typed `1.0` envelopes with request/correlation IDs and UTC timestamps
- Dependencies: `fleetiq-contracts`, `fleetiq-observability`, injected
  trip/job repositories, Redis/database readiness resources, and stream sinks

Camera packets are:

```text
4-byte unsigned big-endian metadata length | UTF-8 JSON metadata | JPEG bytes
```

The live socket uses one-slot subscriber queues. A slow consumer can lose
intermediate state but receives the newest available state. Durable risk
events remain an HTTP/repository concern.

## Configuration

Production startup is strict and requires:

```text
FLEETIQ_REDIS_URL
FLEETIQ_DATABASE_URL
FLEETIQ_ALLOWED_ORIGINS=https://fleet.example
```

Optional limits are `FLEETIQ_MAX_METADATA_BYTES` and
`FLEETIQ_MAX_FRAME_BYTES`. Wildcard CORS is rejected because credentialed
requests are enabled. The built-in production dependency placeholders report
readiness as degraded until concrete Redis/PostgreSQL adapters are injected;
they never claim a connection that was not established.

## Run and validate

```powershell
uv run --package fleetiq-api pytest apps/api/tests -v
uv run --package fleetiq-api uvicorn fleetiq_api.main:create_app --factory
```

Tests set `FLEETIQ_TESTING=true` or call `create_app(testing=True)` and use
lifespan-managed in-memory resources. No test requires Redis, PostgreSQL, AWS,
or network access.

Source and tests are committed. Runtime secrets, uploaded frames, logs, and
generated evidence are not.
