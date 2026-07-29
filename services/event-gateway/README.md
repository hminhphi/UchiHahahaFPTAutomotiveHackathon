# FleetIQ Event Gateway

Transport boundary for versioned FleetIQ MQTT events. Paho connection details
live in `transport.py`; contract validation, topic identity checks, dispatch,
QoS, retain policy, and dead-letter behavior live in `handler.py`.

## Protocol

- Telemetry: QoS 0, never retained.
- Risk, coaching, acknowledgements, and dead letters: QoS 1, never retained.
- Service status: QoS 1 and retained.
- Images and raw invalid payloads are never published to MQTT.

Run locally with `fleetiq-event-gateway`. Configure
`FLEETIQ_MQTT_HOST`, `FLEETIQ_MQTT_PORT`, `FLEETIQ_MQTT_TLS`,
`FLEETIQ_MQTT_USERNAME`, and `FLEETIQ_MQTT_PASSWORD`.
