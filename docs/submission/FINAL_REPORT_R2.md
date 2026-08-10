# FleetIQ Guardian: Final Report, Round 2

## Required Intake

| Field | Value |
| --- | --- |
| Team ID / team name | UchiHahaha |
| Team lead / email | `[CONFIRM OFFICIAL TEAM LEAD AND EMAIL]` |
| Solution | FleetIQ Guardian: Remote Driver Intelligence and Collision Risk Platform |
| Reported build | `v1.0.0`, 2026-08-10 |
| Final report | `FINAL_REPORT_R2.pdf` or the organizer-approved final document format |
| Graded demo video | `[FILL VERIFIED REVIEWER-ACCESSIBLE URL]` |
| Evidence folder | `[FILL VERIFIED REVIEWER-ACCESSIBLE URL]` |
| Relevant directions | Digital Cockpit; Connected Car Services; Vehicle Middleware; AI-assisted safety analytics |

| Member | GitHub | Primary ownership |
| --- | --- | --- |
| Phi | `hminhphi` | Road-facing camera, automotive integration, perception delivery |
| Trung | `hoangtrung1801` | In-cabin DMS and driver-state CV |
| Dung | `VKUNeMo` | AI agent/NLP and coaching intelligence |
| Kha | `khaphan11` | CV/AI-ML training, depth, detection, lane evaluation |
| Tu | `four2k3` | AI agent, backend/software integration, dashboard support |

## 1. Solution Overview

FleetIQ Guardian is a fleet-manager operations console that turns historical road camera frames, driver-camera signals, depth, and organizer telemetry into ranked trip risk, timestamped evidence, and bounded coaching context. The primary user is a fleet safety manager reviewing completed trips; the buyer is a fleet operator or OEM safety analytics team.

The reviewer-visible outcome is a ranked ten-trip fleet view. A reviewer can open a risky trip, replay the road-left video, scrub synchronized road-right, driver, and depth followers, inspect custom-YOLO detections with depth-derived distance/TTC, read the DMS state, and trace the fused score.

## 2. Core Flow and Current Scope

```text
Road-left frames -> custom YOLO v3 labels -> depth ROI distance/TTC -> road artifact
Driver frames -> DMS state artifact ---------------------------------> fusion artifact
Telemetry ------------------------------------------------------------> fusion artifact
Road/DMS/fusion artifacts -> FastAPI -> Next.js operations console
```

The current final build processes all scored organizer trips `T01d` through `T10d`.

| Component | Current state |
| --- | --- |
| Custom YOLO v3 object labels | Real, batch-generated for 17,999 frames |
| YOLOP road/lane masks | Real pretrained inference; used for segmentation overlay only |
| GT-depth ROI distance and TTC proxy | Real computation on provided depth keyframes; nearest previous depth keyframe is used for sparse depth frames |
| DMS timeline | Real precomputed model/pseudo-label artifact path; normalized to organizer output vocabulary for CSV |
| Fusion risk index | Real deterministic artifact generation from available road, DMS, and telemetry signals |
| Fleet dashboard, road-left MP4 replay, frame overlays | Real, Docker-compose deployed and browser-smoke tested |
| CarSky bridge/HMI | Partial. The bridge container is part of the system; Android Automotive HMI must be shown separately before claiming end-to-end IVI execution. |

## 3. Baseline and Team-Owned Delta

| Baseline / provided capability | Team-owned implementation |
| --- | --- |
| Organizer stereo frames, depth maps, telemetry, driver frames, and redacted scored trips | Canonical trip artifacts, detection label export, depth-distance/TTC integration, DMS and fusion artifacts, API routes, operational dashboard, replay synchronization, and submission CSV validator |
| Team-kit fixed-ROI StereoSGBM TTC baseline | Custom YOLO v3 road-object detector trained on LocateAnything labels; detection-aware TTC evidence rather than an image-only fixed ROI |
| YOLOP pretrained road/lane segmentation | Separation of YOLOP masks from the custom object detector; YOLOP is not claimed as the primary object detector |
| Raw camera files | Packaged road-left MP4, frame map, byte-range streaming, road mask, depth, and DMS overlays in the browser |

If the team-owned integration is removed, the raw dataset and baseline remain, but a reviewer cannot inspect the ten-trip fleet ranking, custom detection evidence, synchronized replay, or organizer-format output files in one workflow.

## 4. Output and Evidence

### O1: Ten-trip Fleet Risk Console

| Field | Evidence |
| --- | --- |
| Claim / outcome | A fleet manager can rank and open all ten scored trips. |
| Pass condition | Fleet overview exposes ten trip cards with score, severity, latest alert, and driver state. |
| Observed result | Browser smoke test found exactly 10 fleet cards. Live API returns T01d-T10d with non-fallback score, severity, and driver state. |
| Status | Real |
| Evidence locator | `http://localhost:3000/`; `GET /api/v1/trips`; `artifacts/trips/fleet_summary.json` |
| Video timestamp | `[FILL AFTER RECORDING]` |
| Caveat | Values are deterministic outputs from available redacted-trip signals; organizer ground truth for scored trips is unavailable locally. |

### O2: Road Risk Evidence at a Visible Motorcycle Event

| Field | Evidence |
| --- | --- |
| Claim / outcome | The custom detector identifies an in-lane motorcycle and associates it with depth evidence. |
| Pass condition | Road analysis for T01d frame 551 contains a `Motorcycle` detection with a non-null depth distance. |
| Observed result | `Motorcycle`, confidence `0.3941`, bbox `(308.30, 196.14)-(345.92, 268.97)`, depth distance about `5.02 m`. |
| Status | Real |
| Evidence locator | `artifacts/trips/T01d/analysis/road/000551.json`; `data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted/T01d/kitti/label2_yolo_v3/000551.txt`; `GET /api/v1/trips/T01d/analysis/road/frames/551` |
| Video timestamp | `[FILL AFTER RECORDING]` |
| Caveat | The model also emits an overlapping pedestrian prediction on this frame due to a conflicting LocateAnything training label. The motorcycle itself is detected; the duplicate class must be disclosed. |

### O3: Synchronized Road Replay and AI Overlay

| Field | Evidence |
| --- | --- |
| Claim / outcome | A reviewer can replay the road-left MP4 and inspect frame-aligned road mask, road object, DMS, depth, and fusion data. |
| Pass condition | The descriptor has a non-empty frame map; MP4 range requests return `206`; browser loads a video element and analysis endpoints without `404`. |
| Observed result | T01d descriptor returns 1,800 frame-map entries at 10 FPS. Next proxy returns video/mp4 with byte range support. Browser smoke test passed. |
| Status | Real |
| Evidence locator | `GET /api/v1/trips/T01d/road-video`; `GET /api/v1/trips/T01d/road-video/content`; `GET /api/v1/trips/T01d/analysis/road/frames/551`; `GET /api/v1/trips/T01d/analysis/road/masks/551` |
| Video timestamp | `[FILL AFTER RECORDING]` |
| Caveat | Depth is sparse at keyframes; the API intentionally uses the nearest previous available depth frame for follower display. |

### O4: Organizer-Format Predictions

| Field | Evidence |
| --- | --- |
| Claim / outcome | The system exports one valid prediction CSV per scored trip for TTC, driver state, and risk score. |
| Pass condition | Each file has the exact organizer header, one row per frame in order, finite-or-`inf` TTC, one accepted driver state, and risk in `[0, 100]`. |
| Observed result | Ten CSVs generated and validated. Each contains 1,800 rows, including T08d's fallback row for its unavailable road image artifact. |
| Status | Real |
| Evidence locator | `predictions/UchiHahaha/T01d.csv` through `T10d.csv`; `tools/dataset/validate_submission.py` |
| Video timestamp | `[OPTIONAL]` |
| Caveat | Organizer `evaluation.py` was run on a full-GT Practice trip. Do not claim scored-trip accuracy until the organizer evaluates redacted trip predictions. |

### O5: Practice-Trip Evaluation

The organizer evaluator ran on `T01-Sample` (600 frames; full ground truth) on 2026-08-10. This is a single holdout-style validation run, not a result for the ten redacted scored trips.

| Predictor | Critical TTC MAE | Critical TTC F1 | TTC composite | False-positive rate |
| --- | ---: | ---: | ---: | ---: |
| Organizer SGBM baseline | 58.595s | 0.125 | 30.6/100 | 0.008 |
| FleetIQ custom detector + depth-ROI TTC | 19.612s | 0.240 | 28.3/100 | 0.058 |

The custom TTC path reduces critical-zone MAE and improves F1 on this trip, but its TTC composite is lower because the evaluator penalizes its higher false-positive rate and inverse-TTC error. This is an improvement target, not an overclaimed win.

| Evidence locator | `artifacts/evaluation/T01-Sample_baseline_evaluation.json`; `artifacts/evaluation/T01-Sample_custom_evaluation.json`; `artifacts/evaluation/custom_predictions/UchiHahaha/T01-Sample.csv` |
| Caveat | The Practice artifact path did not invoke the trained DMS runtime, so its Challenge 2 all-`alert` fallback result and the trivial Challenge 3 result are excluded from performance claims. |

## 5. Technical Quality and Reproducibility

| Evidence | Observed result |
| --- | --- |
| Custom detector | YOLO v3 best checkpoint: mAP50 `0.40952` at epoch 43. |
| DMS checkpoint | Best validation accuracy `95.17%`. |
| Batch scope | 17,999 custom YOLO label files: 1,800 each for T01d-T07d and T09d-T10d; 1,799 image labels for T08d with valid CSV fallback coverage for all 1,800 frame IDs. |
| API/browser smoke | 10 fleet cards; T01d road-left video element; road mask, depth, road, DMS, and fusion artifact routes returned successfully. |
| Automated checks | `32 passed`: submission-format, historical replay, trajectory, and roadface pipeline-contract tests. |

Reproduce the final artifact and CSV state:

```powershell
uv run python tools/dataset/export_yolo_labels.py --dataset redacted
uv run python services/roadface-worker/tests/generate_ai_artifacts.py --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted --output-dir artifacts/trips --label-dir-name label2_yolo_v3
uv run python tools/dataset/export_submission.py --team UchiHahaha --trip T01d --trip T02d --trip T03d --trip T04d --trip T05d --trip T06d --trip T07d --trip T08d --trip T09d --trip T10d
uv run python tools/dataset/validate_submission.py --predictions-dir predictions/UchiHahaha
uv run python data/team-kit/Package_starterkit/package_starterkit/team_kit/evaluation.py --predictions artifacts/evaluation/custom_predictions/UchiHahaha/T01-Sample.csv --trip-dir data/Practice_Dataset/Practice_Dataset/T01-Sample --output artifacts/evaluation/T01-Sample_custom_evaluation.json
```

## 6. Platform Utilization and Ecosystem Alignment

FleetIQ uses a control-plane API and Web dashboard to consume evidence artifacts, with a CarSky bridge/HMI path for bounded coaching acknowledgement. The Docker demo runs API, Web, MinIO, Redis, PostgreSQL, MQTT, model mock, and CarSky bridge components. The browser workflow is real. The CarSky Android Automotive view is **not** included as a verified step in this final browser pass and must be recorded separately if claimed as end-to-end platform evidence.

## 7. User, Buyer, and Deployment Path

| Topic | Statement |
| --- | --- |
| Direct user | Fleet safety manager, trip reviewer, or operations analyst |
| Buyer / decision owner | Fleet operator, logistics safety owner, or OEM analytics team |
| Product form | B2B fleet-safety analytics and driver-coaching platform |
| Workflow change | Replace manual video review with ranked risk queue, replayable evidence, and targeted coaching context |
| Deployment dependencies | Camera/depth ingestion, model runtime, object storage, API/Web control plane, and optional CarSky/IVI integration |

## 8. Limitations and Disclosure

1. Scored detached trips intentionally hide TTC, driver-state, and risk ground truth. Local output is not a claim of organizer-scored accuracy.
2. YOLO v3 is the selected detector because it outperformed the later v4 finetune. Its mAP50 remains moderate and rare classes are imbalanced.
3. LocateAnything labels can conflict. T01d frame 551 demonstrates a valid motorcycle detection plus an overlapping false pedestrian label; this is visible evidence, not suppressed from the report.
4. YOLOP is used for drivable-road/lane masks only. It has a one-class vehicle detector in this setup and missed the motorcycle in the cited frame; it is not claimed as the primary object detector.
5. TTC uses depth ROI and collision-cone filtering. It is an explainable proxy and requires organizer evaluation on Sample trips before claiming quantitative accuracy.
6. CarSky browser-to-bridge integration exists in the project, but Android Automotive end-to-end proof must be captured separately before submission if included in the claim.
7. A recorded video must reflect this exact build. Edited/cut video, manual setup, and any simulated component must be disclosed in the video timestamp map.

## 9. Graded Video Timestamp Map

| Output ID | Target timestamp | What the reviewer sees | Disclosure |
| --- | --- | --- | --- |
| O1 | `00:00-00:25` | Fleet overview with ten ranked trips | Historical, precomputed organizer-trip analysis |
| O2 | `00:25-01:20` | T01d drill-down and frame 551 motorcycle evidence | Explain the overlapping pedestrian false positive honestly |
| O3 | `01:20-02:05` | Road-left replay, mask, depth, DMS, and fusion synchronization | Precomputed local artifacts served by Docker demo stack |
| O4 | `02:05-02:30` | Submission CSV directory and validator output | Redacted-trip scoring occurs only on organizer infrastructure |
| Platform | `02:30-03:00` | CarSky bridge/HMI proof, only if recorded live | Mark manual hardware/IVI steps explicitly |

Replace the target timestamps with actual recorded timestamps before submitting.

## 10. Mentor Verification Notes

1. Open `http://localhost:3000` and confirm ten fleet cards load.
2. Open T01d and confirm road-left video loads.
3. Scrub to frame 551 and confirm the custom road analysis contains `Motorcycle`.
4. Confirm road-mask, depth, DMS, and fusion overlays move with the selected frame.
5. If CarSky is claimed, verify the Android HMI acknowledgement flow separately.

## Team Confirmation

- [ ] This report, video, and evidence folder correspond to the stated build.
- [ ] Reviewer access to every URL has been checked in an incognito/private browser session.
- [ ] Real, partial, simulated, and manual components are disclosed accurately.
- [ ] The CSV directory has been validated after its final team-folder rename.
- [ ] The team acknowledges that the organizer records the submitted packet at its received timestamp.

| Field | Value |
| --- | --- |
| Team representative | `[FILL BEFORE SUBMISSION]` |
| Completion date | `[FILL BEFORE SUBMISSION]` |
| Final report filename | `[FILL BEFORE SUBMISSION]` |
