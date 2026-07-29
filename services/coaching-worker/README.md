# FleetIQ Coaching Worker

Converts medium-to-critical risk events into bounded, deduplicated coaching
commands and delivers them through CarSky.

Critical in-motion messages are deliberately short. Low-risk events do not
interrupt the driver. The real adapter requires `CARSKY_BASE_URL`,
`CARSKY_API_KEY`, `CARSKY_ROOM_ID`, and `CARSKY_NODE_KEY`; tests and local
development use `MockCarSkyAdapter`.
