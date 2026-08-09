# Automotive Hackathon Proposal Plan

## Project Name

**FleetIQ Guardian: Remote Driver Intelligence & Collision Risk Platform**

## Proposal Objective

Build an out-car fleet monitoring platform that turns multi-view camera data, in-car camera signals, depth/ground-truth labels, and simulated sensor-fusion telemetry into actionable fleet safety intelligence.

The system will help Fleet Managers and OEM Analytics teams answer three questions:

1. Which driver, vehicle, or trip is currently risky?
2. Why is the risk high, with timestamped evidence?
3. What coaching or operational action should be taken next?

## Hackathon Positioning

The strongest proposal path is to target **Challenge #3: Driver Intelligence Platform** as the main submission, while implementing the core of **Challenge #1** and **Challenge #2** as reliable modules underneath it.

This gives the team a high-scoring product story while keeping execution risk manageable:

- Challenge #1 provides the explainable safe-driving score engine.
- Challenge #2 provides TTC and near-miss risk detection.
- Challenge #3 fuses both into one fleet-level intelligence platform.

The pitch should be:

> We built a remote fleet intelligence layer that converts raw telemetry and camera streams into explainable trip scores, collision-risk events, driver-state insights, and coaching recommendations for fleet managers.

## Dataset Understanding

The starter dataset supports all three verticals from one shared source.

Available signals:

- `data/T01/kitti/image_2`: left road-facing RGB camera
- `data/T01/kitti/image_3`: right road-facing RGB camera or stereo pair
- `data/T01/kitti/depth`: depth map per frame
- `data/T01/kitti/calib`: camera calibration
- `data/T01/driver`: in-cabin driver camera, not temporally composed
- `data/T01/T01.json.gz`: ground-truth labels and sensor-fusion simulation

Starter-kit outputs:

- Loaded trip data
- Road camera, driver camera, depth, and ground truth access
- Baseline TTC predictor around 50/100 scoring using SGBM plus ROI median
- Notebook to visualize driver state timeline, TTC, risk, and sample frames
- README with API reference and submission format

Important interpretation:

- The challenge is not asking for a full self-driving stack.
- The expected output is an out-car monitoring system for fleet managers.
- Video and telemetry are evidence streams; the judged product is the dashboard, event log, scoring, report, and alert intelligence.

## Option Analysis

### Option A: Challenge #1 Only - Fleet Safe Driving Score Engine

This is the lowest-risk route.

Advantages:

- Easiest to complete within hackathon time.
- Scoring can be made explainable and stable.
- Dashboard and report outputs are straightforward.
- Strong fit for Fleet Manager needs.

Weaknesses:

- Less technically differentiated.
- May look like a rules dashboard unless supported with good evidence clips and behavior timeline.
- Does not fully exploit multi-view camera and depth data.

Recommended only if the team has very limited implementation bandwidth.

### Option B: Challenge #2 Only - Vision-Based Collision Risk Monitor

This is the most technical route.

Advantages:

- Uses road cameras, stereo/depth, calibration, object labels, and telemetry well.
- TTC and near-miss detection are compelling in a live demo.
- Easier to beat the provided TTC baseline with smoothing, confidence, and better event logic.

Weaknesses:

- False positives can hurt perceived quality.
- TTC quality is sensitive to depth noise, object association, and frame-to-frame stability.
- A pure TTC demo may feel narrow from a product standpoint.

Good for teams with strong perception or computer vision focus.

### Option C: Challenge #3 - Driver Intelligence Platform

This is the highest-upside route and the recommended submission.

Advantages:

- Best product story for judges.
- Uses the full dataset: road cameras, in-car camera, depth, telemetry, ground truth, and fusion signals.
- Combines scoring, near-miss detection, behavior analytics, dashboard, and coaching.
- Can still succeed even if some AI modules are baseline-level, because the integration and explainability matter.

Weaknesses:

- Requires disciplined scope control.
- Needs a clean event schema and time alignment pipeline.
- Dashboard must feel polished and useful to non-engineers.

Recommended as the main strategy.

## Recommended Proposal

Submit **FleetIQ Guardian** as a **Driver Intelligence Platform** for remote fleet monitoring.

The system will have three core engines:

1. **Trip Safety Score Engine**
   - Scores every trip from 0 to 100.
   - Breaks down score by driver attention, vehicle handling, lane behavior, speeding, and collision risk.
   - Produces auditable explanations for every deduction.

2. **Vision-Based Collision Risk Engine**
   - Computes frame-level or segment-level TTC.
   - Detects near-miss events.
   - Uses depth, stereo camera signals, lead-object labels, and ego telemetry.
   - Outputs severity, confidence, and evidence frame windows.

3. **Driver Intelligence Fusion Engine**
   - Aligns driver state, road risk, and telemetry events on one trip timeline.
   - Produces a unified risk score.
   - Generates coaching insights such as "late braking while distracted" or "repeated lane drift at high speed".

## Differentiation Strategy

The proposal should emphasize five differentiators:

1. **Evidence-first scoring**
   - Every score deduction links to a timestamp, event type, confidence, and visual evidence.

2. **Cross-signal fusion**
   - Risk is higher when unsafe driving behavior and road danger happen together, such as drowsiness plus short TTC.

3. **Baseline-plus improvement**
   - The team will start from the provided TTC baseline and improve it with temporal smoothing, confidence scoring, event consolidation, and context-aware thresholds.

4. **Fleet-manager UX**
   - The dashboard is designed for non-engineers: ranking, alerts, trend panels, trip drill-down, and coaching summary.

5. **Deployable architecture**
   - The design separates ingestion, feature extraction, scoring, API, and dashboard so it can scale from one trip to many vehicles.

## Technical Architecture

### Data Layer

Inputs:

- Road-facing multi-view image frames
- Depth maps
- Calibration files
- In-car driver frames
- Ground-truth labels
- Simulated telemetry and sensor-fusion events

Outputs:

- Normalized trip records
- Frame-level risk streams
- Event logs
- Trip score reports
- Dashboard-ready JSON

### Event Schema

Use one canonical event schema across all modules.

Required fields:

- `event_id`
- `trip_id`
- `vehicle_id`
- `driver_id`
- `start_ts`
- `end_ts`
- `source`: `telemetry`, `road_camera`, `driver_camera`, `depth`, `fusion`
- `event_type`
- `severity`: 1 to 5
- `confidence`: 0 to 1
- `score_impact`
- `explanation`
- `evidence`

Example event types:

- `speeding`
- `harsh_brake`
- `harsh_steering`
- `lane_departure`
- `short_ttc`
- `near_miss`
- `drowsiness`
- `distraction`
- `compound_risk`

### Scoring Formula

Start with a transparent rule-based score because it is easier to explain during judging.

Suggested score:

```text
final_score = 100
  - handling_penalty
  - attention_penalty
  - collision_risk_penalty
  - lane_behavior_penalty
  + recovery_bonus
```

Suggested category weights:

- Driver state: 25%
- Collision risk and TTC: 35%
- Vehicle handling: 25%
- Lane and road behavior: 15%

Fusion multipliers:

- Drowsy or distracted plus short TTC: increase severity by 1 level.
- High speed plus lane offset: increase score impact.
- Braking response after TTC drop: reduce final penalty slightly if response is timely.
- Repeated events within a short window: consolidate into one stronger event instead of noisy duplicates.

### TTC Engine

Minimum viable TTC logic:

1. Use ground-truth or detected lead-object ROI when available.
2. Estimate object distance using depth map median inside ROI.
3. Smooth distance over time.
4. Estimate relative closing speed from distance delta and ego speed.
5. Compute TTC when relative closing speed is positive.
6. Trigger risk events when TTC crosses thresholds.

Risk levels:

- `Low`: TTC above 4.0 seconds
- `Medium`: TTC from 2.5 to 4.0 seconds
- `High`: TTC from 1.5 to 2.5 seconds
- `Critical`: TTC below 1.5 seconds

Improvements over baseline:

- Temporal smoothing to reduce flicker.
- Confidence score based on depth stability and object continuity.
- Event merging to avoid repeated noisy alerts.
- Context-aware severity using ego speed, braking, and driver state.

### Driver State Engine

MVP approach:

- Use provided driver-state labels or starter-kit outputs if available.
- Convert driver state into time segments.
- Normalize into states such as `attentive`, `distracted`, `drowsy`, and `unknown`.

Stretch approach:

- Add lightweight visual inference for eye closure, head pose, or distraction if labels are insufficient.
- Keep model output explainable as evidence segments rather than opaque classifications.

### Dashboard

Primary views:

- Fleet overview with risk cards and latest alerts
- Driver ranking by score and risk trend
- Trip detail page with synchronized timeline
- TTC chart with event markers
- Driver-state timeline
- Evidence frame viewer
- Coaching report panel

Do not build a marketing landing page. The first screen should be the operational fleet dashboard.

### API

Minimum endpoints:

- `GET /api/fleet/summary`
- `GET /api/drivers/ranking`
- `GET /api/trips/{trip_id}`
- `GET /api/trips/{trip_id}/events`
- `GET /api/trips/{trip_id}/score`
- `GET /api/trips/{trip_id}/ttc`
- `POST /api/trips/analyze`

## Demo Flow

The demo should be short and concrete.

1. Open fleet dashboard.
2. Show a ranked driver or vehicle with high risk.
3. Drill into one trip.
4. Show timeline where TTC drops and driver state is unsafe.
5. Open evidence frame or clip.
6. Show score breakdown and explanation.
7. Show coaching recommendation.
8. Mention optional back-to-car alert as future extension.

Best demo story:

> This trip scored 62 because the driver had repeated short-TTC events, two harsh braking events, and one compound event where attention dropped while the vehicle was closing on a lead object. The fleet manager can inspect the evidence and assign targeted coaching.

## Judging Rubric Alignment

### Innovation

Strong because the system fuses driver state, road risk, and telemetry into a single explainable risk intelligence layer.

### Feasibility

Strong because it starts from the provided starter kit and improves baseline outputs rather than depending on a large custom model.

### Technical Depth

Strong because it uses depth, stereo road cameras, calibration, TTC estimation, time alignment, event scoring, and signal fusion.

### Business Value

Strong because fleet safety, driver coaching, incident review, and OEM analytics are direct use cases.

### Demo Quality

Strong if the dashboard is polished, the timeline is synchronized, and each alert has evidence.

## Implementation Plan

### Phase 0: Project Setup

Deliverables:

- Repository structure
- Dataset loader
- Canonical event schema
- Mock dashboard data contract

Acceptance criteria:

- One trip can be loaded.
- Road frames, driver frames, depth, and telemetry can be referenced by timestamp.
- A sample trip summary JSON can be generated.

### Phase 1: Scoring Engine

Deliverables:

- Telemetry event extraction
- Driver-state event extraction
- Trip score computation
- Score breakdown JSON

Acceptance criteria:

- Every score deduction has an explanation.
- The same input produces stable score output.
- Score can be shown per trip, driver, and vehicle.

### Phase 2: TTC and Near-Miss Engine

Deliverables:

- TTC stream
- Risk levels per timestamp
- Near-miss event list
- Confidence score

Acceptance criteria:

- TTC stream beats the baseline qualitatively by being smoother and more useful.
- Critical events are consolidated into readable alert windows.
- Each event links to evidence frames.

### Phase 3: Fusion Engine

Deliverables:

- Unified event log
- Compound risk events
- Unified risk score
- Coaching recommendations

Acceptance criteria:

- The system can explain why an event is more severe when multiple signals align.
- Dashboard can filter by event type, driver, vehicle, and risk level.

### Phase 4: Dashboard and Report

Deliverables:

- Fleet overview dashboard
- Driver ranking
- Trip drill-down
- TTC and driver-state timeline
- Event evidence panel
- Post-trip coaching report

Acceptance criteria:

- A judge can understand the system within 30 seconds.
- A judge can inspect one risky event without developer explanation.
- The report can be exported or rendered as a shareable artifact.

### Phase 5: Final Demo Package

Deliverables:

- 3-minute demo script
- Architecture diagram
- Evaluation summary
- Screenshots
- Backup static demo data

Acceptance criteria:

- Demo works without live model failures.
- All visualizations can run from prepared outputs.
- The team can still present if one optional module fails.

## Team Roles

### Product and Pitch Lead

Owns:

- Final proposal narrative
- Demo script
- Judging rubric mapping
- Slide story

### Data and Perception Lead

Owns:

- Dataset loading
- Depth and TTC computation
- Road-camera evidence extraction
- Quality checks against baseline

### Driver State and Fusion Lead

Owns:

- Driver camera signals
- Time alignment
- Compound risk event logic
- Coaching recommendation rules

### Backend Lead

Owns:

- Event schema
- Scoring APIs
- Trip analysis pipeline
- JSON outputs for dashboard

### Frontend Lead

Owns:

- Fleet dashboard
- Trip drill-down
- Timelines and charts
- Evidence panel and report view

## Risk Register

### Risk: Dataset time alignment is messy

Mitigation:

- Normalize all signals to frame index first.
- Convert to timestamps only after alignment is stable.
- Keep a fallback sample trip with manually verified alignment.

### Risk: TTC is noisy

Mitigation:

- Smooth depth and TTC over a rolling window.
- Use confidence and event merging.
- Judge risk by event windows instead of isolated frames.

### Risk: Driver camera labels are weak

Mitigation:

- Treat driver state as optional confidence modifier.
- Build fusion so road risk and telemetry still work without perfect driver labels.

### Risk: Dashboard takes too long

Mitigation:

- Build dashboard from static JSON first.
- Add live API only after the UI story is stable.

### Risk: Too much scope

Mitigation:

- Keep Challenge #3 as pitch, but define MVP as score + TTC + one fused trip drill-down.
- Put back-to-car alerts and advanced ML as stretch goals.

## MVP Definition

The minimum winning demo should include:

- One fleet overview screen
- One driver ranking table
- One trip detail view
- One synchronized timeline with TTC, driver state, and telemetry events
- One score breakdown
- One near-miss event with visual evidence
- One coaching recommendation

This is the core product. Everything else is optional polish.

## Stretch Goals

Add these only after the MVP works:

- Remote back-to-car advisory message
- Annotated video export with TTC overlay
- Map heatmap of risky route segments
- PDF or JSON trip report export
- Comparison against baseline TTC score
- Lightweight model for driver distraction or drowsiness

## Proposal Summary

FleetIQ Guardian is a practical and judge-friendly proposal because it uses the full starter dataset while avoiding a risky full-autonomy scope. It turns camera, depth, driver state, and telemetry into a product that fleet managers can actually use: ranking, alerts, event evidence, risk score, and coaching.

The recommended path is to submit under **Challenge #3**, implement Challenge #1 and Challenge #2 as core engines, and demo a polished end-to-end trip intelligence workflow.

## Progress Status (2026-08-10)

### Completed

- [x] LocateAnything labeling: 17,999/17,999 frames (100%) across T01d–T10d, 14,291 frames with ≥1 box
- [x] DMS training: 95.17% val accuracy (epoch 7), checkpoint at `artifacts/models/dms/best_sequence_model.pt`
- [x] YOLO v2 training: 100 epochs complete, best mAP50=0.40952 at epoch 43
- [x] PR #47 merged: Driver behavior detection with phone use (cam-driver-phone-use branch)
- [x] Depth endpoint fixed and verified
- [x] Road video streaming working
- [x] DMS analysis returning real per-frame state
- [x] Custom dataset export: 13,668 train / 1,760 val / 1,844 test with per-trip 80/10/10 split from label2_custom
- [x] Dark mode tokens applied to UI (Geist font + dark theme)
- [x] Web container rebuilt and deployed with updated styles

### In Progress

- [ ] YOLO v4 finetune: epoch 33/50, best mAP50=0.393 at epoch 13 (training in progress)
- [ ] Fix trajectory UI flip issue (video shows left turn but trajectory shows right)

### Next Actions

- [ ] Wait for YOLO v4 training completion (patience=20, likely to finish around epoch 45-50)
- [ ] Regenerate artifacts for T01d–T10d with new YOLO v4 model
- [ ] Verify object detection appears on dashboard trip pages
- [ ] Debug trajectory coordinate mapping (check if lon/lat or camera frame inverted)
- [ ] Prepare final demo script and presentation
- [ ] Verify Challenge #2 TTC/near-miss implementation works end-to-end

## Next Action Checklist

- [x] Confirm final challenge category as Challenge #3.
- [x] Build the canonical trip and event schema.
- [x] Load one sample trip from the starter kit.
- [x] Generate baseline score and TTC JSON.
- [x] Build dashboard from static JSON.
- [x] Add scoring and TTC APIs.
- [x] Add evidence frames and timeline markers.
- [ ] Prepare final proposal slides and 3-minute demo.
