# FleetIQ Event Protocol v1

FleetIQ uses schema version `1.0` for compact JSON payloads shared across
applications, workers, and MQTT. Every event preserves a correlation ID, trip,
frame index, producer, and timezone-aware occurrence time. Unknown fields are
rejected.

## MQTT Topics

| Payload | Topic | QoS |
| --- | --- | --- |
| `TelemetryEvent` | `fleetiq/v1/vehicles/{vehicle_id}/telemetry` | 0 |
| `RiskEvent` | `fleetiq/v1/trips/{trip_id}/risk` | 1 |
| `CoachingCommand` | `fleetiq/v1/vehicles/{vehicle_id}/coaching/command` | 1 |
| `CoachingAck` | `fleetiq/v1/vehicles/{vehicle_id}/coaching/ack` | 1 |

Only service-status messages may be retained. MQTT transports event metadata,
commands, and artifact references only. It never carries camera or depth bytes.

## Risk Event Sample

```json
{
  "schema_version": "1.0",
  "event_id": "f993e723-485e-441a-b75d-0cfcf6b4eb1f",
  "correlation_id": "trip-01:frame-100",
  "trip_id": "T01-Sample",
  "frame_index": 100,
  "producer": "fusion-worker",
  "occurred_at": "2026-07-28T00:00:00Z",
  "event_type": "short_ttc",
  "severity": 4,
  "confidence": 0.91,
  "explanation": "TTC below 1.5 seconds",
  "evidence": [
    {
      "artifact_uri": "s3://fleetiq-evidence/T01-Sample/frames/000100.jpg",
      "frame_index": 100,
      "description": "Road-facing frame at minimum TTC"
    }
  ]
}
```

The generated [JSON Schema](schemas/events-v1.json) defines this payload and
every other public v1 model: `EventEnvelope`, `TelemetryEvent`, `RiskEvent`,
`CoachingCommand`, `CoachingAck`, `InferenceRequest`, and `InferenceResponse`.
