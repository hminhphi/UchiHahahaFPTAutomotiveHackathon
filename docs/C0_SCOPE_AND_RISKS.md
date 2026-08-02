# FleetIQ Scope And Risks

## Must-Have C3 Demo

FleetIQ Guardian is submitted as Challenge #3, with Challenge #1 scoring and
Challenge #2 road risk as integrated engines. The judge-facing MVP is one
historical trip that can be ranked, replayed, explained, and coached.

1. Fleet priority screen with transparent aggregate score and severity.
2. Historical road replay served from MinIO through a binary WebSocket.
3. Frame-synchronised route marker, speed, longitudinal/lateral acceleration,
   DMS state, valid TTC/headway, active scenario event, and evidence context.
4. Explainable risk/coaching record and mock CarSky acknowledgement path.
5. Reproducible `8/8` Compose smoke test and three-minute demonstration.

## Verified Delivery Gates

- Full CPU workspace suite: `234 passed`.
- Ruff and `uv lock --check`: pass.
- Dashboard unit tests and production build: pass.
- Compose configuration and historical-trip smoke path: `8/8`.
- Android Automotive HMI Docker builder: Kotlin unit tests and debug APK pass.
- AWS CDK application synthesis: pass without deploying infrastructure.

## Deliberately Bounded

- No autonomous driving, control command, steering, brake, or throttle output.
- No claim that organizer simulator labels are model predictions.
- No claim that the local SageMaker-compatible endpoint is a deployed model.
- No claim of RDS persistence until the PostgreSQL repository adapter is complete.

## Team Ownership

| Owner | Role | Primary boundary |
| --- | --- | --- |
| Phi (`hminhphi`) | AI/Automotive | Road-facing data, distance, TTC, system integration |
| Tu (`four2k3`) | AI/software | Next.js operations dashboard and CarSky HMI |
| Trung (`hoangtrung1801`) | AI/CV | In-cabin DMS and state smoothing |
| Kha (`khaphan11`) | CV/ML | Model contracts, training/evaluation support |
| Dung (`VKUNeMo`) | AI/NLP | API, fusion, coaching language, event flow |

## Stack And Resources

- Python 3.12 with `uv`; Next.js 15 with pnpm.
- Docker Compose, MinIO, Redis, PostgreSQL, Mosquitto, local model mock, and
  local CarSky bridge for reproducible integration.
- AWS target: ECS EC2 for web/API, S3 for historical evidence, SageMaker for
  model endpoints, and IoT Core for MQTT ingress.
- Practice Dataset: six 30-second, 20 Hz historical simulator trips.

## Five Highest Risks

| Risk | Mitigation | Demo fallback |
| --- | --- | --- |
| Road labels omit off-lane objects | Ego-lane/road-mask filtering and custom-label audit | Use recorded organizer targets as explicit reference evidence |
| Stereo/TTC noise | ROI median, temporal filtering, confidence and collision-cone guard | Show `No valid TTC`; never substitute adjacent-lane TTC |
| Curved/occluded lane mask | Ground plane, calibrated horizon, one-sided evidence rules | Keep lane result as degraded rather than fabricate corridor |
| DMS model generalisation | Label-backed reference state plus temporal smoothing | Label output remains visibly marked as organizer telemetry |
| Live demo dependency failure | MinIO historical replay, mock endpoints, `8/8` smoke test | Use prepared local Compose run and recorded evidence route |
