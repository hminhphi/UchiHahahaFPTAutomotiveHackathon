# FleetIQ API

The API is the HTTP and WebSocket control plane owned by the backend team. It
handles trip queries, idempotent analysis jobs, camera ingress, and latest live
trip state. Long-running inference belongs in workers and SageMaker; camera
bytes never use MQTT.

## Interfaces

- HTTP: `/health/live`, `/health/ready`, `/api/v1/trips`, `/api/v1/trips/{trip_id}/trajectory`, `/api/v1/jobs`
- Camera WebSocket: `/ws/v1/trips/{trip_id}/camera/{view}`
- Live-state WebSocket: `/ws/v1/trips/{trip_id}/live`
- Inputs: versioned JSON requests and binary JPEG frame packets
- Outputs: typed `1.0` envelopes with request/correlation IDs and UTC timestamps
- Dependencies: `fleetiq-contracts`, `fleetiq-observability`, injected
  trip/job repositories, Redis/database readiness resources, and stream sinks

## Historical Replay And Trip Analytics

When `FLEETIQ_REPLAY_ENABLED=true`, the API lists and reads historical Practice
Dataset trips through either the filesystem or the configured S3-compatible
object store. A viewer connection to `road_left`, `road_right`, or `driver`
starts an ordered replay for that trip/view. Viewer queues intentionally start
empty: the first received frame belongs to the current replay rather than a
cached frame from a previous viewer session.

`GET /api/v1/trips/{trip_id}/trajectory` returns one point per organizer frame.
The dashboard uses the binary camera packet `frame_index` to select the same
point for world route position, speed, longitudinal/lateral acceleration,
driver state, alertness, finite TTC/headway, active scenario events, and
simulator risk. Infinite TTC/headway values are serialized as `null`; consumers
must not replace them with an unrelated target's TTC.

Fleet list summaries expose a documented baseline `safety_score` calculated
from aggregate near misses, handling flags, speeding time, and driver
alertness. It is an explainable dashboard baseline because the supplied
organizer `safe_driving_score` is zero for all Practice trips; it is not a
trained-model result.

Camera packets are:

```text
4-byte unsigned big-endian metadata length | UTF-8 JSON metadata | JPEG bytes
```

The camera socket supports producer and viewer clients on the same
`trip_id/view`. Browser dashboards connect as viewers with the default URL. A
frame producer should connect with `?role=producer`; when it sends a valid
binary packet, the API stores the latest decoded frame, returns an
acknowledgement to the producer, and broadcasts the original packet to connected
viewers so the dashboard can render it as a blob URL.

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
$env:FLEETIQ_TESTING = "true"; uv run --package fleetiq-api uvicorn fleetiq_api.main:create_app --factory
```

Tests set `FLEETIQ_TESTING=true` or call `create_app(testing=True)` and use
lifespan-managed in-memory resources. No test requires Redis, PostgreSQL, AWS,
or network access.

Source and tests are committed. Runtime secrets, uploaded frames, logs, and
generated evidence are not.
