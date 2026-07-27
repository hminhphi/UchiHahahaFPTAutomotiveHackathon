# FleetIQ Guardian - AI Image Prompts

Use these prompts directly in an AI image generator. Each prompt is self-contained because the image generator may not know the project context.

## Slide 1 - Cover Hero

```text
Create a hero image for "FleetIQ Guardian", an Automotive Hackathon proposal product. Context: this is a full-vertical remote fleet safety intelligence platform using multi-view road cameras, in-cabin driver camera, depth maps, calibration, ground-truth labels, and simulated telemetry/sensor fusion. The product converts raw video and telemetry into explainable risk events, trip score, fleet dashboard, and optional back-to-car IVI coaching. Scene: a professional fleet operations control room with a large dashboard wall showing connected vehicles, road-camera tiles, driver-state indicators, TTC/collision-risk timeline, trip score, and a safe IVI coaching loop back to a car. Visual style: FPT Automotive hackathon deck style, deep navy #19226D background, orange #F37021 accents, blue #034EA2 system elements, white dashboard panels, clean enterprise UI, cinematic but realistic, high contrast. Avoid: readable fake text, brand logos, cartoon style, generic startup gradients, cluttered tiny labels.
```

## Slide 3 - Raw Signals To Action

```text
Create a split-screen visual for the FleetIQ Guardian proposal. Context: FleetIQ Guardian is a remote fleet safety intelligence platform for Automotive Hackathon, turning multi-view road camera, driver camera, depth, labels, and telemetry into actionable fleet decisions. Left side: messy raw inputs, including road-facing camera frames, in-cabin driver camera, depth-like heatmap, speed/brake/steering telemetry traces. Right side: clean Fleet Manager output with risk score, near-miss event timeline, evidence card, driver behavior status, and coaching recommendation. The story should be "raw signals become explainable action." Style: enterprise automotive dashboard, deep navy #19226D, orange #F37021 risk highlights, blue #034EA2 platform accents, white cards, clean PowerPoint-ready composition. Avoid: readable fake text, excessive detail, consumer app look, decorative blobs.
```

## Slide 4 - Dataset Advantage

```text
Create a clean technical dataset-capability matrix for the FleetIQ Guardian Automotive Hackathon proposal. Context: one shared starter dataset supports all verticals: multi-view road cameras, driver-facing camera, depth maps, camera calibration, ground-truth labels, and simulated telemetry/sensor fusion. Show these input sources as rows or left-side modules. Show capabilities as columns or right-side modules: Safe Driving Score, TTC/Collision Risk Monitor, Driver Monitoring/DMS, Multimodal Fusion, Fleet Dashboard, Back-to-Car IVI Coaching. Use crisp automotive icons, white cards, and a navy #19226D background with orange #F37021 and blue #034EA2 accents. Make it look like a polished proposal slide, not a spreadsheet. Avoid readable fake text, tiny labels, or random stock vehicle imagery.
```

## Slide 6 - Road-view Intelligence

```text
Create a road-view intelligence mockup for FleetIQ Guardian. Context: the system uses road-facing multi-view cameras, depth maps, calibration, and telemetry to detect vehicles, track objects, estimate distance, relative velocity, relative acceleration, TTC, lane boundaries, and lane offset. Scene: realistic dashcam/front-road view on a highway or urban road. Overlay: detected vehicles with bounding boxes, distance markers in meters, relative velocity arrows, TTC risk indicator, lane lines, lane offset indicator, and confidence styling. Use clean safety visualization overlays in orange #F37021 for risk and blue #034EA2 for normal system annotations. This should look like evidence used in a fleet risk event, not a video game HUD. Avoid readable fake text, clutter, sci-fi effects, and inaccurate oversized UI.
```

## Slide 7 - Driver Intelligence / DMS

```text
Create an in-cabin Driver Monitoring System mockup for FleetIQ Guardian. Context: FleetIQ Guardian fuses driver-facing camera with road risk and telemetry to detect fatigue, drowsiness, distraction, eye closure, phone use, seatbelt missing, and attention state. Scene: a privacy-conscious in-cabin camera panel showing a driver silhouette or lightly anonymized face, with subtle computer-vision overlays around eyes/head pose and a side panel of DMS signals. Required visual elements: eye closure timeline, attention/drowsiness status, gaze-off-road indicator, phone distraction icon, seatbelt status, confidence meter. Style: enterprise automotive safety UI, navy #19226D, orange #F37021 for risk, blue #034EA2 for system state, white cards. Avoid readable fake text, invasive surveillance feel, scary facial recognition vibe, cartoon style.
```

## Slide 8 - Sensor Fusion And Time Alignment

```text
Create a technical time-alignment visualization for FleetIQ Guardian. Context: the platform aligns three sources: road-view video, driver-facing video, and simulated sensor-fusion telemetry such as speed, brake state, steering angle, throttle, turn signal, and lane offset. Show a horizontal timeline with synchronized rows: road camera frames, driver camera frames, depth/TTC signal, speed/brake/steering traces, and a highlighted 1-5 second risk event window. The visual should explain how raw streams become an aligned multimodal feature vector. Style: clean proposal diagram, navy #19226D header, orange #F37021 event highlight, blue #034EA2 telemetry lines, white background panels. Avoid readable fake text, overly tiny charts, or decorative abstract waves.
```

## Slide 10 - Risk Case Library

```text
Create a six-card risk event library UI for FleetIQ Guardian. Context: FleetIQ Guardian classifies multimodal driving risk by fusing road camera outputs, driver camera DMS signals, and telemetry. Show six risk cards: near-miss from low TTC, rear collision risk from close rear vehicle plus harsh braking, distracted driving at speed, unsafe lane change with side vehicle, unsafe turn with no signal, lane drift with no signal. Each card should include small signal chips, severity indicator, confidence cue, and an evidence thumbnail placeholder. Style: dense enterprise fleet dashboard, deep navy #19226D, orange #F37021 for high risk, blue #034EA2 for normal signals, white cards, crisp icons. Avoid readable fake text, cartoon icons, and random unrelated safety warnings.
```

## Slide 11 - Trip Score Engine

```text
Create a trip score report UI mockup for FleetIQ Guardian. Context: the product outputs an explainable Safe Driving Score from 0-100 per trip, driver, and vehicle by aggregating road risk, driver state, vehicle handling, and lane behavior. Show a central trip score, breakdown bars or donut chart, event timeline with near-miss and DMS markers, evidence thumbnails, and a coaching recommendation panel. The score must feel auditable: every deduction links to severity, duration, confidence, and evidence. Style: professional fleet analytics dashboard, navy #19226D, orange #F37021 for deductions/risk, blue #034EA2 for safe/system data, white cards. Avoid readable fake text, unrealistic metrics overload, consumer fitness-app style.
```

## Slide 12 - Fleet Manager Dashboard

```text
Create the main Fleet Manager dashboard mockup for FleetIQ Guardian. Context: FleetIQ Guardian is an out-car platform for OEM/Fleet Manager monitoring, using video and telemetry to rank drivers, detect near-miss events, score trips, and provide evidence. Dashboard elements: fleet risk overview, driver/vehicle ranking table, live map with risk-colored vehicles, near-miss heatmap, TTC timeline, driver behavior analytics panel, alert log, score breakdown, and evidence thumbnails. Include a hint of remote back-to-car IVI coaching status but keep the dashboard as the main product. Style: dense but clean enterprise operations UI, FPT Automotive hackathon palette with navy #19226D, orange #F37021, blue #034EA2, white panels. Avoid readable fake text, stock market dashboard look, decorative gradients, and tiny illegible labels.
```

## Slide 13 - Back-to-Car / IVI Coaching

```text
Create an in-vehicle infotainment (IVI) coaching mockup for FleetIQ Guardian's back-to-car bonus. Context: FleetIQ Guardian normally runs as an out-car fleet dashboard, but high-confidence risk events can be safely sent back to the car as IVI coaching or advisory messages. Show a modern cockpit infotainment screen with subtle safety coaching: following-distance advisory, speed advisory, attention reminder, and post-trip coaching card. Include a small safety gate concept visually: confidence passed, fallback available, non-distracting alert. Style: minimal automotive HMI, dark navy #19226D, orange #F37021 only for urgent risk, blue #034EA2 for advisory/system state, clean and calm. Avoid alarming red overload, readable fake text, distracting UI, or implying autonomous vehicle control.
```

## Slide 15 - Implementation Roadmap

```text
Create a polished 16:9 PowerPoint roadmap visual for "FleetIQ Guardian" by team UchiHaha, an Automotive Hackathon proposal. Context: FleetIQ Guardian is a full-vertical Driver Intelligence Platform that uses multi-view road cameras, in-cabin driver camera, depth maps, calibration, labels, and simulated telemetry to detect explainable risk events, calculate trip score, show a fleet dashboard, and optionally send safe IVI coaching back to the car. The slide must show a 3-week Round 2 execution roadmap with three horizontal columns or lanes:

Week 1 - Data & Physics Foundation: dataset loader, timestamp synchronization, camera calibration, depth ROI, road-plane sanity check, object tracking, TTC baseline, DMS baseline, telemetry normalization.

Week 2 - Risk Intelligence Core: aligned feature windows, GBDT fusion model, confidence calibration, trip score engine, risk event schema, scenario replay harness, semantic risk-cluster labeling by a small LLM only after clustering, not for model training.

Week 3 - Product Demo & Safety Loop: Fleet Manager dashboard, evidence pack export, post-trip coaching report, alert log, shadow-mode IVI coaching, safety gate with confidence threshold, cooldown, fallback, and intervention log.

Add a thin bottom storyboard labeled visually, not with detailed readable text: "Input trip -> synchronized event -> explainable score -> coaching / IVI shadow mode". Include innovation callouts as small badges: Scenario Replay, Evidence Pack, Risk Cluster Library, Shadow-mode IVI, Acceptance Gates. Visual style must match FPT Automotive hackathon deck: deep navy #19226D background, orange #F37021 for milestones and risk, blue #034EA2 for connectors and system flow, warm white panels, clean enterprise automotive UI, minimal professional, high contrast, no clutter. Use simple icons for dataset, camera, clock sync, model, dashboard, report, IVI, safety gate. Avoid readable fake paragraphs, random brand logos, generic Gantt chart, cartoon style, exaggerated sci-fi effects, and fake precise metrics.
```

## Slide 17 - Evaluation And Safety

```text
Create an evaluation and safety scorecard visual for FleetIQ Guardian. Context: FleetIQ Guardian is an automotive fleet risk intelligence system, so reviewers care about false alarms, TTC stability, score explainability, latency, and safe back-to-car behavior. Show metric cards for: TTC smoothing/stability, false alarms per hour, recall at critical risk, score auditability, DMS confidence, latency budget, and back-to-car safety fallback. Include a subtle safety-gate motif before IVI coaching. Style: enterprise automotive AI validation slide, navy #19226D, orange #F37021 for risk metrics, blue #034EA2 for system metrics, white cards, clean and credible. Avoid readable fake text, fake benchmark numbers that look too precise, alarmist styling.
```

## Slide 18 - Closing Product Loop

```text
Create a closing slide visual for FleetIQ Guardian showing the full safety improvement loop. Context: FleetIQ Guardian is a full-vertical Automotive Hackathon platform that uses road cameras, driver camera, depth, labels, and telemetry to detect risk, explain evidence, score trips, coach drivers, and improve fleet safety. Visual: circular loop with five stages: Detect, Explain, Score, Coach, Improve. Include connected vehicle, fleet dashboard, evidence frame, trip score report, and IVI coaching hint. Style: high-impact professional proposal graphic, deep navy #19226D, orange #F37021 highlights, blue #034EA2 connectors, white panels, clean enterprise automotive feel. Avoid readable fake text, generic circular arrows without automotive context, cartoon style.
```
