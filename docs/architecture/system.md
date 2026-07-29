# System Architecture

FleetIQ Guardian converts synchronized road cameras, driver state, depth,
calibration, and telemetry into explainable trip risk and bounded coaching.

## Runtime Flow

1. Road and driver streams are submitted as bounded binary WebSocket frames.
2. Telemetry and risk events use versioned MQTT topics and JSON contracts.
3. Roadface and DMS inference use local adapters during development and named
   SageMaker endpoints in AWS.
4. Fusion aligns frame identity, TTC, lane state, handling, and driver state.
5. The API exposes fleet/trip data while the Next.js dashboard shows evidence.
6. Safety-gated coaching is delivered to the CarSky Android HMI and acknowledged.

The detailed processing view is maintained in
[`diagrams/00_fleetiq_processing_pipeline.puml`](diagrams/00_fleetiq_processing_pipeline.puml).

## Protocol Boundaries

| Boundary | Protocol | Rule |
| --- | --- | --- |
| Browser to API | HTTPS | Queries, jobs, health, and reports |
| Camera producer to API | WSS binary | 4-byte big-endian metadata length, JSON metadata, JPEG bytes |
| Vehicle and services | MQTT | Versioned `fleetiq/v1/...` topics; no camera bytes |
| Worker to model | SageMaker HTTPS or local HTTP | Versioned inference request/response |
| Backend to CarSky bridge | HTTPS | Bounded coaching command with idempotency and expiry |

Canonical contracts live in `packages/contracts`; protocol documentation and
exported schemas live in [`docs/protocols/`](../protocols/README.md).

## Deployment

Local integration uses the Compose profiles described in
[`infra/compose/README.md`](../../infra/compose/README.md). AWS runs web/API on
ECS EC2 behind a TLS ALB and model inference on four private SageMaker
endpoints. The Android HMI runs in the CarSky Skycraft guest, not ECS.

## Safety And Degradation

- Every score deduction and coaching command references an explainable event.
- Low-confidence models may degrade to mock or unavailable state; the UI must
  show that state rather than presenting fabricated certainty.
- Driver distraction can increase an existing road-risk severity but cannot
  create an unsafe driving command by itself.
- The current production database adapter is incomplete, so persistent AWS
  operation remains a documented release gate.
