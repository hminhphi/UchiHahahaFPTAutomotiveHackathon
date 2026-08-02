# Three-Minute Demo Script

## 0:00-0:20 - Fleet Priority

Open `http://localhost:3000`. Explain that FleetIQ Guardian is a remote fleet
intelligence layer: it ranks past or live trips, provides timestamped evidence,
and turns a risky moment into a bounded coaching action. Open `T01-Sample`.

## 0:20-1:10 - Synchronized Evidence

Point to the road-facing replay and the telemetry cards. Explain that the data
is one historical organizer trip stored in MinIO, not a browser fixture. Use a
risk-event chip to pause and jump directly to its evidence frame, then scrub a
few frames around it. The player can enter full screen for incident review. As
the selected frame changes, speed, longitudinal and lateral acceleration, DMS
state, and the route marker update from the same trajectory index.

Call out the TTC card carefully: `No valid TTC` is a correct result when no
target is in the simulator collision cone. Do not substitute a TTC from an
adjacent-lane object. When a valid simulator TTC/headway is present, the card
shows it with the corresponding active scenario event.

## 1:10-1:55 - Vehicle Dynamics and Route

Scroll to the speed-coloured trajectory. Blue represents 0 km/h and red
represents 100 km/h or above. Geometry comes directly from `ego.location.x/y`;
FleetIQ does not integrate noisy acceleration to invent a route. The `NOW`
vehicle icon is the current camera frame. Orange and gold markers represent
filtered harsh-brake and fast-corner contexts.

## 1:55-2:35 - Explainability and Coaching

Show the evidence queue, timeline, and coaching card. Explain that each shown
item is derived from a frame-level telemetry measurement and retains its frame,
time, source, and severity. A score-signal that has no source data displays as
`N/A`; the demo does not fabricate lane or distance evidence. The current local
CarSky bridge is a clearly labelled mock acknowledgement path; it never
commands steering, braking, or throttle.

## 2:35-3:00 - Architecture and Reliability

Summarize the deployment shape: web/API on ECS EC2, models on SageMaker,
historical evidence in S3, event metadata through MQTT, and camera streaming
through WebSocket. The player uses a same-origin HTTP proxy for
exact frame seeks, while WebSocket remains the transport for live camera
streams. Run or show the `8/8` local smoke test result. It verifies the API,
MinIO replay, event boundary, model mock, and CarSky acknowledgement.
