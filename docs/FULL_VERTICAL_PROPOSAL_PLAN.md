# FleetIQ Guardian - Full Vertical Proposal Plan

## 1. Re-evaluation of the Updated Brief

The updated brief makes one thing very clear: the strongest submission is not a single isolated model. It is a **full out-car fleet intelligence product** that uses the shared starter dataset across all verticals, then adds a controlled **remote back-to-car** loop as a bonus.

The three challenge blocks should be interpreted as three capability layers:

- **Safe Driving Score Engine:** stable, auditable 0-100 scoring per trip, driver, and vehicle.
- **Collision Risk Monitor:** camera-based TTC, near-miss event detection, severity and evidence.
- **Driver Intelligence Platform:** fusion of driver state, road risk, telemetry, dashboard, analytics, and coaching.

The bonus layer is:

- **Remote Back-to-Car / IVI Coaching:** send selected alerts, coaching notifications, or speed advisories back into the car, with latency budget, confidence threshold, and safety fallback.

### Important Positioning

The proposal should not say "we are doing three separate challenges." It should say:

> We build one integrated FleetIQ Guardian platform. The three challenge outputs become three product capabilities: scoring, collision risk, and driver intelligence. The bonus back-to-car loop closes the fleet-to-vehicle feedback cycle.

This is stronger for reviewers because it sounds like a product system, not a collection of disconnected models.

## 2. Final Product Concept

**FleetIQ Guardian** is a remote fleet safety intelligence platform that converts road camera, driver camera, depth, calibration, labels, and simulated telemetry into:

- real-time risk events,
- explainable trip score,
- fleet dashboard,
- event evidence,
- driver behavior analytics,
- post-trip coaching,
- optional IVI speed advisory / attention alert / coaching feedback.

### One-line pitch

FleetIQ Guardian turns raw multi-view video and telemetry into explainable fleet risk intelligence, then safely closes the loop back to the vehicle through IVI coaching.

### Reviewer-facing promise

Fleet managers do not need more raw video. They need to know **who is risky, why it is risky, where the evidence is, and what action to take next**.

## 3. System Method Overview

### 3.1 Road-view model

Inputs:

- multi-view road cameras,
- stereo/depth frames,
- calibration,
- road-facing labels.

Outputs:

- object class and track ID,
- object distance,
- relative velocity and acceleration,
- TTC,
- lane boundaries,
- lane offset,
- lane departure risk,
- evidence frame references.

Method:

- Object detection/classification for vehicles, pedestrians, obstacles.
- Tracking across frames for object continuity.
- Distance estimation from depth ROI and single-view road-plane geometry.
- Relative velocity from distance history.
- Relative acceleration from smoothed velocity deltas.
- TTC only when closing speed is positive.
- Lane detection and lane offset to capture drift/unsafe lane behavior.

References:

- `Real-time Vehicle Distance Estimation Using Single View Geometry`
- `Multi-camera Bird's Eye View Perception for Autonomous Driving`
- `SurroundOcc`
- `Cam4DOcc`
- `6D-VNet` as optional future extension for vehicle pose/orientation.

### 3.2 Sensor-fusion normalizer

Inputs:

- speed,
- brake state,
- steering angle,
- throttle,
- turn signal,
- lane offset,
- simulator metadata.

Outputs:

- normalized vehicle state vector,
- timestamp-aligned ego motion features,
- missing-data and confidence flags.

Method:

- Resample telemetry to shared frame index.
- Normalize units and range.
- Derive ego acceleration, braking intensity, steering jerk, harsh maneuver flags.
- Use as context for scoring and risk severity.

### 3.3 Driver camera / DMS model

Inputs:

- driver-facing video,
- optional starter driver-state labels.

Outputs:

- fatigue probability,
- drowsiness probability,
- distraction probability,
- eye closure duration,
- gaze-off-road duration,
- phone use probability,
- seatbelt missing probability,
- confidence.

Method:

- Eye/face tracking and temporal smoothing.
- Drowsiness/fatigue detection using eye closure and attention signals.
- Unsafe behavior classification: phone use, seatbelt missing, long off-road gaze.
- Output is not a final risk by itself; it becomes a context signal for fusion.

References:

- `Real-Time Sleepiness Detection for Driver State Monitoring System`
- `Intelligent Driver Monitoring Systems: A Survey of Drowsiness Detection Technologies for Road Safety`
- `Optimized Driver Fatigue Detection Method Using Multimodal Neural Networks`
- `Early Drowsiness Detection via Second-Order Derivative Analysis of Heart Rate Variability`

### 3.4 Multimodal risk intelligence

Inputs:

- road context vector,
- vehicle state vector,
- driver state vector.

Outputs:

- risk label,
- severity,
- confidence,
- explanation,
- evidence URI,
- recommended action.

Method:

- Align all streams by frame index and timestamp.
- Create rolling windows of 1s, 3s, and 5s.
- MVP model: rule seed + GBDT/LightGBM/XGBoost-style tabular classifier.
- Stronger model: TCN/GRU/Tiny Transformer over multimodal feature windows.
- Risk embeddings/events are clustered after inference to discover recurring patterns.
- LLM 4B-8B only assigns semantic labels to completed clusters for analytics.
- LLM labels are not added to the training dataset or used to train the risk model.
- LLM is not part of real-time safety inference.

Reference:

- Multimodal fatigue papers support fusion logic.
- TTC and BEV papers support road-risk feature design.
- DMS survey supports confidence, false-alarm control, and operational metrics.

### 3.5 Trip score engine

Inputs:

- risk events,
- severity,
- duration,
- confidence,
- driver state,
- road context,
- vehicle handling.

Outputs:

- score 0-100,
- score breakdown,
- top risk reasons,
- post-trip report,
- coaching recommendation.

Recommended scoring:

```text
trip_score = 100
  - road_risk_penalty
  - driver_state_penalty
  - vehicle_handling_penalty
  - lane_behavior_penalty
  + recovery_bonus
```

Penalty:

```text
penalty = base_weight(label)
        x severity
        x duration_factor
        x confidence
        x context_multiplier
```

Examples:

- low TTC + high closing speed: multiplier 1.5
- distracted + ego speed > 5 km/h: multiplier 1.3
- side vehicle + sharp steering: multiplier 1.4
- braking response after TTC drop: recovery bonus

### 3.6 Remote back-to-car / IVI coaching

This is the bonus layer and should be presented carefully.

Outputs:

- real-time IVI advisory,
- haptic/voice/visual attention alert,
- speed advisory,
- post-trip coaching notification,
- intervention log.

Safety gate:

- Only high-confidence events pass.
- Latency budget must be respected for real-time warning.
- If confidence or connection is weak, fallback to fleet dashboard / post-trip coaching.
- Avoid alert fatigue: consolidate repeated events and cap warning frequency.
- Never send aggressive or ambiguous interventions.

Examples:

- Critical TTC + high closing speed -> "Increase following distance."
- Distraction at speed -> "Eyes on road."
- Repeated lane drift -> post-trip coaching card.
- Harsh braking while rear vehicle close -> event review, not necessarily in-car alert.

## 4. Recommended Proposal Deck Structure

This section describes the deck only. Do not create slides yet.

### Slide 1 - Cover

Title:

**FleetIQ Guardian**

Subtitle:

**Full Vertical Fleet Safety Intelligence with Back-to-Car IVI Coaching**

Content:

- Challenge scope: all verticals from shared starter dataset.
- One-line pitch: raw video + telemetry -> risk intelligence -> safer fleet action.

Figure/mockup:

- Hero visual showing fleet dashboard + connected vehicle loop.

AI image prompt:

`Professional automotive fleet safety operations scene, connected vehicles monitored from a fleet control dashboard, road camera feeds, driver state signals, risk score, and IVI coaching loop, FPT Automotive hackathon style, deep navy #19226D and orange #F37021, clean enterprise UI, cinematic but realistic, no readable fake text.`

### Slide 2 - What The Brief Is Really Asking For

Purpose:

Reframe the challenge as one integrated platform.

Content:

- Out-car monitoring is the required core.
- Score, TTC, and driver intelligence are three outputs of one system.
- Back-to-car is optional but high-value bonus.
- Dataset is shared across all verticals.

Figure/mockup:

- Use `08_full_vertical_product_map`.

Diagram:

- `artifacts/diagrams/08_full_vertical_product_map.png`

### Slide 3 - Product Thesis

Headline:

**Fleet Managers do not need more raw video. They need explainable action.**

Content:

- Raw video is hard to inspect.
- Single alerts create noise.
- Fleet decisions need event evidence, score, ranking, and coaching.
- FleetIQ converts signals into decisions.

Figure/mockup:

- Split visual: raw streams on left, actionable dashboard/report on right.

AI image prompt:

`Split-screen enterprise automotive safety visual: left side raw road-camera frames, driver camera, telemetry traces; right side clean fleet dashboard with risk score, event timeline, evidence card, and coaching recommendation, deep navy and orange palette, professional pitch deck style, no readable fake text.`

### Slide 4 - Dataset Advantage

Purpose:

Show that the starter pack supports the full system.

Content:

- Road cameras: object/lane/TTC.
- Driver camera: attention/drowsiness/distraction.
- Depth/calibration/labels: distance and evidence.
- Telemetry/sensor fusion: speed, brake, steering, turn signal.
- One trip can feed all verticals.

Figure/mockup:

- Dataset matrix: input source x capability.
- Optional small dataset folder screenshot.

AI image prompt:

`Clean technical dataset matrix for automotive hackathon: rows road cameras, driver camera, depth maps, calibration, labels, telemetry; columns score engine, TTC risk, DMS, fusion, dashboard, back-to-car coaching; FPT navy orange style, white cards, crisp icons.`

### Slide 5 - End-to-End Solution Flow

Purpose:

Give the reviewer the whole system in one 16:9 friendly diagram.

Content:

- Inputs.
- Per-source models.
- Aligned feature windows.
- Risk intelligence.
- Fleet outputs.
- Offline learning loop.

Diagram:

- `artifacts/diagrams/07_deck_solution_flow.png`

Figure/mockup:

- No AI image needed; use diagram.

### Slide 6 - Road-view Intelligence

Purpose:

Explain how road camera becomes distance/TTC/lane risk.

Content:

- Detect/classify vehicles and obstacles.
- Track objects.
- Estimate distance via depth ROI + single-view geometry.
- Compute relative velocity/acceleration.
- Compute TTC and lane offset.

Diagram:

- `artifacts/diagrams/01_road_view_model.png`

Reference:

- Real-time Vehicle Distance Estimation Using Single View Geometry.
- Multi-camera BEV Perception.
- SurroundOcc.
- Cam4DOcc.

Figure/mockup:

- Annotated road frame: vehicles with distance, rel speed, TTC, lane offset.

AI image prompt:

`Road-facing vehicle camera frame mockup with detected cars, lane lines, distance meters, relative velocity arrows, TTC labels, lane offset indicator, clean safety visualization overlay, realistic dashcam view, no readable fake text except simple numeric-style labels.`

### Slide 7 - Driver Intelligence / DMS

Purpose:

Show DMS is not only drowsiness; it is driver risk context.

Content:

- Fatigue/drowsiness.
- Distraction/gaze off-road.
- Eye closure duration.
- Phone use.
- Seatbelt missing.
- Confidence and temporal smoothing.

Diagram:

- `artifacts/diagrams/02_driver_dms_model.png`

Reference:

- Real-Time Sleepiness Detection.
- DMS Survey.
- Multimodal Fatigue Detection.
- HRV Drowsiness Detection as future sensor extension.

Figure/mockup:

- Driver camera analysis card with face landmarks/attention meter.

AI image prompt:

`In-cabin driver monitoring UI mockup showing driver face camera, eye closure signal, attention score, drowsiness risk, phone distraction indicator, seatbelt status, clean enterprise automotive dashboard style, navy orange accents, privacy-conscious visual, no readable fake text.`

### Slide 8 - Sensor Fusion And Time Alignment

Purpose:

Explain how telemetry becomes reliable context, not another model-heavy branch.

Content:

- Normalize speed, brake, steering, throttle, turn signal.
- Align latency between video and telemetry.
- Create rolling windows.
- Add missing-data and confidence flags.

Figure/mockup:

- Timeline with road frame, driver frame, telemetry row, aligned event window.

AI image prompt:

`Technical timeline visualization for automotive sensor fusion: road video frames, driver camera frames, speed/brake/steering telemetry traces, aligned event window highlighted, clean navy white orange presentation diagram, precise and readable.`

### Slide 9 - Multimodal Risk Intelligence

Purpose:

Make the AI method believable and reviewer-friendly.

Content:

- Rule-based is good for seed labels and guardrails.
- Final online model should be lightweight learned model.
- Risk outputs are clustered offline; LLM adds semantic labels after clustering.
- LLM-generated cluster labels are never used for model training.
- Online detector predicts risk class, severity, confidence.

Diagram:

- `artifacts/diagrams/03_training_and_labeling_loop.png`

Reference:

- DMS survey for false-alarm metrics.
- Multimodal fatigue detection for fusion.
- TTC papers for risk labels.

Figure/mockup:

- No AI image needed; use diagram.

### Slide 10 - Risk Case Library

Purpose:

Show concrete cases reviewers can understand.

Content:

Examples:

- Low TTC + high closing speed -> near-miss.
- Rear vehicle close + ego harsh brake -> rear collision risk.
- Distracted + speed > 5 km/h -> distracted driving risk.
- Side vehicle + sharp steering -> side-swipe risk.
- Intersection turn + no signal -> unsafe turn.
- Lane drift + no signal -> lane departure/no-signal event.

Diagram:

- `artifacts/diagrams/06_risk_case_examples.png`

Figure/mockup:

- Grid of 6 event cards with icon, input signals, risk label, coaching action.

AI image prompt:

`Six-card automotive risk event library UI: near miss, rear collision risk, distracted driving, unsafe lane change, unsafe turn no signal, lane drift no signal; each card has signal chips, severity color, evidence thumbnail placeholder; deep navy orange blue enterprise style.`

### Slide 11 - Trip Score Engine

Purpose:

Prove the score is explainable, auditable, and fair.

Content:

- Score 0-100 per trip/driver/vehicle.
- Four components: road risk, driver state, vehicle handling, lane behavior.
- Severity x duration x confidence x context multiplier.
- Recovery bonus for safe response.
- Exportable score breakdown.

Diagram:

- `artifacts/diagrams/04_trip_scoring_model.png`

Figure/mockup:

- Score breakdown donut/bar + event list.

AI image prompt:

`Fleet safety trip score report UI showing score 72/100, breakdown bars for road risk, driver state, vehicle handling, lane behavior, event timeline with evidence thumbnails, coaching recommendations, clean enterprise dashboard, navy orange blue palette, no readable fake text.`

### Slide 12 - Fleet Manager Dashboard

Purpose:

Show product output, not just algorithms.

Content:

- Fleet ranking.
- Live risk map.
- Event log.
- Near-miss heatmap.
- Driver behavior analytics.
- Trip drill-down.
- Evidence viewer.

Diagram:

- `artifacts/diagrams/05_dashboard_system_architecture.png`

Figure/mockup:

- Main dashboard mockup.

AI image prompt:

`Modern fleet manager safety dashboard for automotive operations: vehicle ranking table, live map with risk colors, near-miss heatmap, TTC timeline, driver behavior panel, alert log, evidence thumbnails, FPT hackathon navy orange style, dense but clean enterprise UI, no readable fake text.`

### Slide 13 - Back-to-Car / IVI Coaching Bonus

Purpose:

Show high-scoring bonus without sounding unsafe.

Content:

- Closed-loop fleet-to-vehicle.
- Real-time alert only for high-confidence events.
- Post-trip coaching for lower-confidence or non-urgent cases.
- Safety gate: latency, confidence, fallback, alert fatigue control.

Diagram:

- `artifacts/diagrams/09_closed_loop_back_to_car.png`

Figure/mockup:

- IVI alert/coaching screen mockup.

AI image prompt:

`In-vehicle infotainment safety coaching mockup: subtle speed advisory, attention reminder, following distance warning, post-trip coaching card, minimal non-distracting UI, automotive cockpit screen, navy orange accents, safety-first design, no readable fake text.`

### Slide 14 - Method References

Purpose:

Show the work is grounded in research, not improvised.

Content:

- Road/BEV/occupancy references.
- Distance/TTC references.
- DMS/fatigue references.
- Fusion/scoring references.
- Vehicle pose as extension.

Diagram:

- `artifacts/diagrams/10_method_reference_stack.png`

Figure/mockup:

- Method stack with paper icons/cards.

Prompt note:

No AI image needed unless you want a polished paper-map visual. Prefer diagram + citation list.

### Slide 15 - MVP And Implementation Roadmap

Purpose:

Convince reviewers the plan is feasible.

Content:

MVP:

- Load one trip.
- Extract road/DMS/telemetry features.
- Generate risk events.
- Score trip.
- Show dashboard and evidence.
- Generate coaching report.

Stretch:

- Back-to-car IVI advisory.
- Annotated video export.
- Route heatmap.
- Learned temporal model.

Figure/mockup:

- 3-phase roadmap: Proposal -> MVP -> Bonus.

AI image prompt:

`Hackathon implementation roadmap timeline with three phases: data pipeline and feature extraction, risk intelligence and trip score, dashboard and back-to-car IVI bonus; automotive navy orange style, compact professional slide graphic.`

### Slide 16 - Demo Storyboard

Purpose:

Show exactly what the final demo will look like.

Content:

Demo path:

1. Fleet overview.
2. Select risky driver/trip.
3. Open synchronized TTC + DMS + telemetry timeline.
4. Inspect evidence moment.
5. Explain score breakdown.
6. Show coaching and optional IVI advisory log.

Diagram:

- `artifacts/diagrams/11_proposal_demo_storyboard.png`

Figure/mockup:

- Use diagram; optionally add mini dashboard screenshots later.

### Slide 17 - Evaluation And Safety

Purpose:

Address reviewer concerns: false alarms, reliability, safety.

Content:

- TTC baseline improvement: smoothing, confidence, event merging.
- Risk model metrics: PR-AUC, false alarms/hour, recall at critical risk.
- Score stability: same trip -> same score.
- DMS: confidence and temporal smoothing.
- Back-to-car: safety gate and fallback.

Figure/mockup:

- Evaluation scorecard with metrics.

AI image prompt:

`Automotive AI evaluation scorecard slide visual: TTC stability, false alarms per hour, critical recall, score explainability, latency budget, safety fallback, presented as clean metric cards in navy orange enterprise style.`

### Slide 18 - Closing / Why We Should Pass

Purpose:

End with a crisp judging argument.

Content:

- Uses the full dataset.
- Covers all verticals.
- Turns raw signals into actionable fleet intelligence.
- Has evidence and explainability.
- Has realistic MVP.
- Adds high-value back-to-car bonus with safety controls.

Figure/mockup:

- Final product loop: Detect -> Explain -> Score -> Coach -> Improve.

AI image prompt:

`Circular product loop for automotive fleet safety: detect, explain, score, coach, improve; connected fleet vehicle and dashboard elements, professional hackathon pitch visual, deep navy orange blue palette, clean high impact.`

## 5. Diagram Assets Created For This Deck

Use these compiled diagram assets:

- `artifacts/diagrams/07_deck_solution_flow.png`
- `artifacts/diagrams/08_full_vertical_product_map.png`
- `artifacts/diagrams/09_closed_loop_back_to_car.png`
- `artifacts/diagrams/10_method_reference_stack.png`
- `artifacts/diagrams/11_proposal_demo_storyboard.png`
- `artifacts/diagrams/01_road_view_model.png`
- `artifacts/diagrams/02_driver_dms_model.png`
- `artifacts/diagrams/03_training_and_labeling_loop.png`
- `artifacts/diagrams/04_trip_scoring_model.png`
- `artifacts/diagrams/05_dashboard_system_architecture.png`
- `artifacts/diagrams/06_risk_case_examples.png`

SVG versions are also available in the same folder and should be preferred if PowerPoint handles them cleanly.

## 6. References By Method Section

### Road scene understanding

- SurroundOcc: Multi-Camera 3D Occupancy Prediction for Autonomous Driving.
- Multi-camera Bird's Eye View Perception for Autonomous Driving.
- Cam4DOcc: Benchmark for Camera-Only 4D Occupancy Forecasting.
- 6D-VNet for future vehicle pose/orientation extension.

### Distance, TTC, relative motion

- Real-time Vehicle Distance Estimation Using Single View Geometry.
- Visual, Auditory, and Audiovisual Time-to-Collision Estimation.
- Real Time Speed Estimation of Moving Vehicles from Side View Images.

### Driver monitoring / DMS

- Real-Time Sleepiness Detection for Driver State Monitoring System.
- Intelligent Driver Monitoring Systems: A Survey of Drowsiness Detection Technologies for Road Safety.
- Optimized Driver Fatigue Detection Method Using Multimodal Neural Networks.
- Early Drowsiness Detection via HRV Derivative Analysis as future sensor extension.

### Fusion, scoring, and coaching

- Use DMS survey for evaluation principles: PR-AUC, false alarm rate, calibration, time-to-detect.
- Use multimodal fatigue paper to justify feature fusion.
- Use TTC and distance papers to justify road-risk features.
- Use FleetIQ's own rule seed + learned calibration plan for trip scoring.

## 7. What To Emphasize To Reviewers

- This is not three disconnected demos. It is one platform with three visible capabilities.
- The product starts out-car, matching the scope note.
- The dashboard is the core deliverable.
- Back-to-car is a bonus path, protected by safety gate and fallback.
- The ML plan is pragmatic: verified labels train a lightweight model; LLM only names post-inference clusters.
- The score is explainable because every deduction links to event, evidence, severity, confidence, and coaching.

## 8. Assets Still Needed From User

Ask for these before making the final PPTX:

- Team name.
- Member names and roles.
- Preferred language: Vietnamese only or bilingual.
- Whether paper figures may be shown directly or should all be redrawn.
- Any real starter-kit screenshots or dataset explorer screenshots.
- Preferred IVI mockup style: subtle safety notification, coaching card, or cockpit alert.
