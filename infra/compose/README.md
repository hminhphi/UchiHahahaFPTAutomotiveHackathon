# Local Compose Topology

This topology is for integration and demo development. Production keeps the
web/API workloads on ECS EC2 and sends model inference to SageMaker.

## Profiles

| Profile | Starts | Purpose |
| --- | --- | --- |
| `core` | PostgreSQL, Redis, MQTT, MinIO, API, web, event gateway | Product and protocol development |
| `perception` | `core` plus local SageMaker-compatible mock | Perception integration without GPU/cloud cost |
| `full` | `perception` plus CarSky bridge | End-to-end demo and coaching acknowledgement |

Profiles list their complete dependency set, so run one profile at a time:

```powershell
Copy-Item .env.example .env
docker compose --profile core up --build
docker compose --profile full up --build
```

Run the full protocol smoke test in another terminal:

```powershell
uv run --group dev python infra/compose/smoke_test.py
```

The smoke test checks API readiness, telemetry MQTT, mock inference, risk MQTT,
the producer camera WebSocket contract, ordered historical replay from MinIO,
the 600-point trajectory/telemetry endpoint, and CarSky acknowledgement.
Override host endpoints with `FLEETIQ_SMOKE_API_URL`,
`FLEETIQ_SMOKE_MODEL_URL`, `FLEETIQ_SMOKE_BRIDGE_URL`,
`FLEETIQ_SMOKE_MQTT_HOST`, and `FLEETIQ_SMOKE_WS_URL`.

## Data And Artifacts

`data/` is mounted read-only at `/data`. At startup, `minio-seed` mirrors
`data/Practice_Dataset/Practice_Dataset` into the `fleetiq-demo` bucket using
the portable key shape `trips/<trip-id>/...`. The API replays those historical
objects over WebSocket; the browser never reads the organizer dataset directly.
Generated outputs go to `/artifacts`. Neither directory is baked into images.
PostgreSQL, Redis, Mosquitto, and MinIO use named volumes.

Open the local MinIO console at `http://localhost:9001` to inspect seeded demo
objects. The application only depends on the S3-compatible API, so AWS uses the
same code path with an S3 endpoint, bucket, and IAM credentials.

The local API intentionally runs with in-memory repositories while the concrete
PostgreSQL adapter is still pending. Redis and PostgreSQL are health-gated now
so the topology is ready for that adapter without claiming persistence that the
current API does not provide.

## Worker Images

The roadface, DMS, fusion, and coaching packages currently expose bounded
JSONL/CLI jobs rather than long-running consumers. Their Dockerfiles are valid
deployment artifacts, but Compose does not pretend they are daemons. Add the
MQTT receive loop and health contract before registering them as services.

## Security Boundary

The `backend` network is internal. Only web, API, MQTT for local tools, model
mock, and CarSky bridge publish host ports. Anonymous MQTT is intentionally
limited to this local configuration; shared environments must enable
authentication and TLS.
