# CarSky Coaching Bridge

This zero-dependency Python service runs as a CarSky Container Node. It accepts
bounded coaching commands from `coaching-worker` and exposes the current command
and acknowledgement state to the Android Automotive guest over the room's
private Ethernet network.

Endpoints:

- `POST /v1/coaching`
- `POST /api/rooms/{room_id}/nodes/{node_key}/commands`
- `GET /v1/coaching/current?vehicle_id=vehicle-1`
- `POST /v1/coaching/{command_id}/ack`
- `GET /health`

The bridge validates schema version, identifiers, severity and display length,
and deduplicates by `dedupe_key`. It never accepts model probabilities or
unbounded report text. For a KUKSA deployment, mirror the accepted JSON into the
approved FleetIQ VSS branch in the Container Node adapter; the REST path remains
the rollback-safe transport for the demo.

Run:

```text
uv run python apps/carsky-hmi/carsky/bridge/bridge.py
```

Build the Zot image:

```text
docker build -f apps/carsky-hmi/carsky/bridge/Dockerfile \
  -t <ZOT_HOST>/fleetiq/carsky-coaching-bridge:0.1.0 \
  apps/carsky-hmi/carsky/bridge
```
