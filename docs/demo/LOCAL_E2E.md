# Local Demo And E2E Acceptance

## Prerequisites

- Docker Desktop is running.
- The organizer Practice Dataset exists at
  `data/Practice_Dataset/Practice_Dataset`.
- Ports `3000`, `8000`, `8080`, `8090`, `1883`, `9000`, and `9001` are free,
  or have been changed in `.env`.

## Start From A Clean Shell

```powershell
Copy-Item .env.example .env
docker compose --profile full up --build
```

Wait for `minio-seed` to finish. It copies the local read-only dataset into the
`fleetiq-demo` bucket as `trips/<trip-id>/...`; camera files are not baked into
the web or API images.

In a second shell run:

```powershell
uv run --group dev python infra/compose/smoke_test.py
```

The expected result is all eight checks:

```text
1/8 API readiness: ok
2/8 telemetry publish: ok
3/8 local inference: ok
4/8 risk event receive: ok
5/8 producer camera WebSocket: ok
6/8 historical camera replay: ok
7/8 fleet and trajectory telemetry: ok
8/8 mock CarSky acknowledgement: ok
```

## Visual Acceptance

Open `http://localhost:3000/trips/T01-Sample` and confirm:

1. Road replay frame count increases continuously rather than stopping after one frame.
2. The replay time, speed, longitudinal acceleration, lateral acceleration,
   DMS state, and TTC/headway card change with the displayed camera frame.
3. The `NOW` vehicle icon moves on the trajectory as the frame advances.
4. The path starts blue at lower speed and becomes warmer as speed rises.
5. A missing collision-cone target shows `No valid TTC`, not an unrelated object TTC.
6. The evidence queue, risk timeline, and score signals are drawn from the
   same frame-level telemetry. A missing signal is shown as `N/A`, never as a
   made-up value.
7. MinIO contains the six `trips/T0*-Sample` prefixes, while `data/` remains
   local and untracked by Git.

## Truth Boundary

| Surface | Demo source | Claim allowed |
| --- | --- | --- |
| Road camera replay | Organizer image frames copied to MinIO | Historical evidence replay |
| Vehicle/DMS/risk cards | Organizer frame-level JSON labels and telemetry | Simulator/reference telemetry |
| Trajectory geometry | `ego.location.x/y` | World-space simulator route |
| Local model endpoint | Deterministic SageMaker-compatible mock | Contract/integration verification only |
| CarSky bridge | Local mock acknowledgement | Coaching delivery interface only |

## Dashboard Score Formula

The organizer `safe_driving_score` field is zero for all six supplied Practice
trips, so it is not displayed as FleetIQ's score. The API produces a documented
prototype aggregate from organizer telemetry:

```text
score = 100
  - min(35, near_miss_count * 3)
  - min(15, harsh_brake_count)
  - min(10, harsh_corner_count * 2)
  - min(15, round(speeding_pct_time * 0.2))
  - round((1 - average_alertness_score) * 20)
```

Severity is derived from that bounded score and the organizer maximum risk
score. This is a transparent dashboard baseline, not a claimed trained model.

The individual score-signal bars are diagnostic context rather than an
additional model score: road risk uses average simulator risk, driver attention
uses average supplied alertness, vehicle handling uses harsh-brake/fast-corner
frame rate, and speed compliance uses the speeding frame rate. Lane behaviour
is not claimed because this replay contract does not yet expose a validated
lane signal.

To stop the demo stack:

```powershell
docker compose --profile full down
```
