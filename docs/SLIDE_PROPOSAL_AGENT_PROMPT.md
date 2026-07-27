# Prompt For AI Agent: Create Automotive Hackathon Proposal Deck

You are an AI Agent specialized in creating high-conviction hackathon proposal decks for automotive safety and AI systems. Create a polished, reviewer-ready PowerPoint proposal deck for the project **FleetIQ Guardian: Remote Driver Intelligence & Collision Risk Platform**.

## Project Context

Project folder:

`C:\Users\admin\Documents\Projects\AutomotiveHacathon`

Use these files as source context:

- Proposal plan: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\AGENTS.md`
- Template deck: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\Template for Teams - Hackathon 2026.pptx`
- PowerPoint skill guidance: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\.codex\skills\pptx\SKILL.md`
- Extracted paper figures: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures`
- Figure manifest: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\manifest.csv`

## Goal

Create a proposal deck that makes reviewers understand quickly:

1. The real fleet safety problem.
2. Why the provided dataset is valuable.
3. What the solution does.
4. Why the technical architecture is feasible.
5. What the hackathon MVP will demo.
6. Why this team/project should pass the proposal round.

The deck should feel confident, practical, and technically credible. It should not feel like a generic AI pitch.

## Core Project Strategy

Submit under:

**Challenge #3 - Driver Intelligence Platform**

Implementation strategy:

- Build **Challenge #1 - Fleet Safe Driving Score Engine** as the score module.
- Build **Challenge #2 - Vision-Based Collision Risk Monitor** as the TTC / near-miss module.
- Fuse both into a remote **Driver Intelligence Platform** for Fleet Manager and OEM Analytics.

Core one-line pitch:

> FleetIQ Guardian turns multi-view camera, in-car driver video, depth, and simulated telemetry into explainable fleet risk scores, near-miss evidence, and driver coaching insights.

## Dataset Signals To Highlight

The deck must clearly show that the project uses the starter dataset deeply:

- Multi-view road cameras around the vehicle.
- In-car driver camera.
- Depth maps.
- Camera calibration.
- Ground-truth labels.
- Simulated telemetry and sensor-fusion signals.
- Starter TTC baseline, improved through smoothing, confidence, event merging, and context-aware severity.

## Visual System

Use the current template style, not a new generic design.

- Canvas: 16:9.
- Main font: `Quattrocento Sans`.
- Fallback: `Arial`.
- Main navy: `#19226D`.
- Primary orange: `#F37021`.
- Secondary blue: `#034EA2`.
- White: `#FFFFFF`.
- Muted gray-blue: `#6B7A90`.
- Light divider: `#CDCCCC`.

Design tone:

- Automotive safety operations.
- Fleet monitoring dashboard.
- Dense but readable.
- High contrast.
- Product-focused, not academic-only.

Avoid:

- Generic startup gradients.
- Slides full of bullet paragraphs.
- Random stock imagery.
- Overly complex paper diagrams pasted without explanation.

## Important Copyright Guidance

The extracted paper figures are available as local references and may be useful for inspiration. Before using any figure directly in the final deck, check the paper license. If license is unclear, redraw the idea as a clean original diagram and cite it as:

`Concept adapted from: <paper title>, <authors>, <year>.`

Preferred approach:

- Use extracted figures to understand the technical story.
- Redraw architecture/flow diagrams in the deck using the template colors.
- Use direct crops only when necessary and with attribution.

## Selected Extracted Figure Assets

Use these selected assets first. They are more relevant than browsing all 990 extracted items.

### Contact Sheets

Use these to browse all extracted candidates:

- `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\contact_sheets\caption_crops_contact_sheet.jpg`
- `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\contact_sheets\embedded_images_contact_sheet.jpg`

### Recommended Assets For The Deck

1. **SurroundOcc / occupancy pipeline**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\2303.09551v2\2303.09551v2_p003_figcap01.png`
   - Use for: architecture inspiration for multi-camera image features -> 3D/occupancy output.
   - Best slide: Architecture or Core Engines.
   - Recommended handling: redraw as FleetIQ pipeline, do not paste raw unless license is verified.

2. **Dense occupancy ground-truth generation**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\2303.09551v2\2303.09551v2_p004_figcap01.png`
   - Use for: explaining why depth/labels/occupancy are valuable for road risk understanding.
   - Best slide: Dataset Advantage.
   - Recommended handling: use as inspiration for "road scene evidence and risk map" visual.

3. **Surround vision / top-view vehicle monitoring**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\2309.09080v2\2309.09080v2_p004_figcap01.png`
   - Use for: explaining multi-view camera around vehicle.
   - Best slide: Dataset Advantage or Problem.
   - Recommended handling: can be used as a small reference image if attribution is added, or redrawn as a clean top-view car diagram.

4. **BEV transformation network overview**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\2309.09080v2\2309.09080v2_p010_figcap01.png`
   - Use for: showing camera images transformed into a shared bird's-eye-view representation.
   - Best slide: Technical Feasibility.
   - Recommended handling: redraw as `multi-view frames -> BEV/risk space -> events`.

5. **Cam4DOcc dataset construction pipeline**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\2311.17663v3\2311.17663v3_p003_figcap01.png`
   - Use for: temporal / 4D scene reasoning inspiration.
   - Best slide: Architecture or Roadmap Stretch Goal.
   - Recommended handling: redraw as `trip timeline -> frame-level risk -> event windows`.

6. **OCFNet system overview**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\2311.17663v3\2311.17663v3_p005_figcap01.png`
   - Use for: forecasting/temporal prediction concept.
   - Best slide: Differentiation or Future Vision.
   - Recommended handling: translate into FleetIQ "current risk + forecast risk" module.

7. **Real-time vehicle distance estimation block diagram**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\Ali_Real-time_vehicle_distance_estimation_using_single_\Ali_Real-time_vehicle_distance_estimation_using_single__p003_figcap01.png`
   - Use for: TTC/distance estimation method.
   - Best slide: TTC Engine.
   - Recommended handling: redraw as `lead object ROI -> depth/distance -> relative speed -> TTC -> risk level`.

8. **Single-view geometry distance estimation**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\Ali_Real-time_vehicle_distance_estimation_using_single_\Ali_Real-time_vehicle_distance_estimation_using_single__p004_figcap01.png`
   - Use for: explaining how distance can be inferred from image geometry.
   - Best slide: Technical Feasibility or TTC Engine.
   - Recommended handling: simplify into one clear geometry annotation.

9. **Vehicle distance estimation sample results**
   - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\Ali_Real-time_vehicle_distance_estimation_using_single_\Ali_Real-time_vehicle_distance_estimation_using_single__p006_figcap01.png`
   - Use for: visual evidence style, bounding boxes, estimated distances.
   - Best slide: Demo Flow or Evidence Panel.
   - Recommended handling: can inspire annotated frame mockup for FleetIQ near-miss evidence.

10. **6D-VNet vehicle pose estimation pipeline**
    - Path: `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures\caption_crops\Wu_6D-VNet_End-To-End_6-DoF_Vehicle_Pose_Estimation_Fro\Wu_6D-VNet_End-To-End_6-DoF_Vehicle_Pose_Estimation_Fro_p003_figcap01.png`
    - Use for: vehicle pose estimation context, object orientation, 3D reasoning from camera.
    - Best slide: Technical Feasibility or Future Vision.
    - Recommended handling: mention as optional extension, not MVP dependency.

## Required Diagrams To Create

Create at least 3 original diagrams. Use Python, Mermaid, PlantUML, or PowerPoint shapes.

### Diagram 1: End-To-End Architecture

Required flow:

`Dataset signals -> Feature/event engines -> Unified risk intelligence -> Fleet dashboard/report/alert`

Include:

- Road multi-view cameras.
- In-car camera.
- Depth/calibration/labels.
- Telemetry/sensor fusion.
- TTC engine.
- Driver-state engine.
- Score engine.
- Fusion engine.
- Dashboard, event log, coaching report.

### Diagram 2: TTC / Near-Miss Engine

Required flow:

`lead object ROI -> depth or geometry distance -> temporal smoothing -> relative closing speed -> TTC -> severity/confidence -> near-miss event`

Make it clear that the project improves the baseline through:

- smoothing,
- confidence,
- event merging,
- context-aware severity.

### Diagram 3: Reviewer Demo Flow

Required flow:

`Fleet dashboard -> high-risk driver -> trip detail -> synchronized timeline -> evidence frame -> score breakdown -> coaching recommendation`

This diagram should make the demo feel real and easy to judge.

## Suggested Deck Structure

Create 12 slides using the existing template patterns:

1. **Cover**
   - Title: `FleetIQ Guardian`
   - Subtitle: `Remote Driver Intelligence & Collision Risk Platform`
   - Challenge: `Challenge #3 - Driver Intelligence Platform`
   - Tagline: `From raw video and telemetry to explainable fleet safety decisions`

2. **Why This Proposal Passes**
   - Map proposal to judging criteria: innovation, feasibility, technical depth, business value, demo quality.
   - Use compact scorecard layout.

3. **Table Of Contents**
   - Team
   - Challenge choice
   - Problem
   - Solution
   - Architecture
   - MVP and roadmap
   - Impact

4. **Team & Ownership**
   - Assign roles clearly: product/pitch, data/perception, fusion/scoring, backend/API, dashboard/demo.
   - If team names are missing, insert placeholders and ask user to provide names.

5. **Dataset Advantage**
   - Show one shared dataset serving all three verticals.
   - Include dataset signal icons or a compact matrix.
   - Mention road cameras, in-car camera, depth, calibration, labels, telemetry/sensor fusion.
   - Use selected assets 2, 3, or 4 as inspiration.

6. **Problem**
   - Core message: Fleet Managers do not need more raw video; they need explainable risk decisions with evidence.
   - Highlight pain points: noisy alerts, no unified score, hard incident review, no coaching insight.

7. **Solution Overview**
   - Present FleetIQ Guardian as an out-car intelligence layer.
   - Show 3 outputs: score, near-miss events, coaching.
   - Use a clean product flow, not academic detail.

8. **Core Engines**
   - Score Engine.
   - TTC / Near-Miss Engine.
   - Driver Intelligence Fusion Engine.
   - Use selected assets 1, 4, 7, and 8 as inspiration.

9. **Architecture**
   - Include Diagram 1.
   - Make it the technical credibility slide.
   - Keep labels short and visually grouped.

10. **Demo Flow**
   - Include Diagram 3.
   - Show a concrete story: a trip scores 62 because of short TTC, harsh brake, and driver distraction.
   - Mention evidence frame and coaching recommendation.

11. **MVP, Roadmap, Risk Control**
   - MVP: one trip end-to-end.
   - Baseline-plus: improve TTC baseline with smoothing/confidence/event merging.
   - Fallback: dashboard from static JSON if live processing fails.
   - Stretch: remote advisory, annotated video export, route heatmap, PDF/JSON report.

12. **Vision / Impact / Thank You**
   - OEM/fleet value.
   - Post-hackathon path.
   - Close with one strong line: `Safer fleets start with evidence, not guesswork.`

## Copywriting Rules

- Write judge-facing content in Vietnamese.
- Technical terms may stay in English when natural: TTC, near-miss, Fleet Manager, OEM Analytics, telemetry, driver state, event log.
- Every slide needs one strong headline and one clear visual.
- Do not write vague claims such as "AI improves safety".
- Instead say exactly what the system outputs: score, event, confidence, evidence, coaching.
- Keep paragraphs short. Use compact cards and diagrams.
- Make the reviewer feel the team has a controlled MVP, not just ambition.

## Asset Requests If Missing

If any of these are not available, ask the user clearly:

- Team name.
- Member names and roles.
- Team logo/avatar.
- Preferred language: Vietnamese only or bilingual.
- Whether direct paper figure reuse is allowed or whether all paper-inspired visuals should be redrawn.
- Any starter-kit screenshots or dataset explorer screenshots.

## AI Image Generation Prompt If Needed

If a dashboard/product mockup image is needed and no screenshot exists, use this prompt:

`Professional automotive fleet operations dashboard in a modern control room, showing multi-camera vehicle telemetry, driver safety score, collision risk timeline, and alert evidence panels, deep navy and orange FPT automotive hackathon color palette, clean enterprise UI, realistic screen mockup, high contrast, no readable fake text.`

If a hero/cover visual is needed, use this prompt:

`Cinematic automotive safety operations scene, connected fleet vehicles represented on a digital monitoring wall, multi-camera perception overlays, collision risk timeline, driver intelligence signals, deep navy and orange color palette, professional enterprise presentation style, realistic but clean, no readable fake text.`

## Deliverables

Create:

- A completed `.pptx` proposal deck in `C:\Users\admin\Documents\Projects\AutomotiveHacathon`.
- A 2-3 minute demo script as Markdown.
- A short asset/citation note listing which paper figures were used directly or redrawn.
- A list of assumptions and missing user-provided assets, if any.

## Quality Checklist

Before finishing, verify:

- The deck follows the existing PowerPoint template.
- The first slide is visually memorable.
- Reviewer can understand the solution in 60 seconds.
- Challenge #3 is clearly the main submission.
- Challenge #1 and #2 appear as engines under the platform.
- Dataset usage is explicit and credible.
- Architecture is clear.
- MVP is realistic.
- Demo flow is concrete.
- Paper visuals are either properly cited or redrawn as original diagrams.
- No slide is just a wall of text.
