# FleetIQ Fusion Worker

Aligns road, driver-state, and telemetry records by trip/frame, then computes a
deterministic explainable risk score.

The score starts at 100 and applies bounded category penalties:

- Collision risk: up to 35.
- Driver attention: up to 25.
- Vehicle handling: up to 25.
- Lane behavior: up to 15.

Compound risk increases severity once when short TTC coincides with distraction
or drowsiness. It does not double-penalize the score.
