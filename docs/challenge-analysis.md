# Challenge Analysis

## Scope note from the brief

The judging context is **out-car fleet monitoring** using telemetry plus driver-facing and road-facing video. Core outputs are remote dashboards, event logs, score reports, and alerts for fleet managers or OEM analytics teams. A reverse loop back to the car is a bonus, not mandatory.

## Challenge 1: Fleet Safe Driving Score Engine

### Goal
Build a scoring engine that outputs a score from 0 to 100 per trip, per driver, and per vehicle.

### Inputs
- Driver-facing video: attention, drowsiness, distraction
- Road-facing video: lane departure, lead vehicle context
- Telemetry: steering, brake, throttle, speed, lane offset

### Required outputs
- Fleet ranking dashboard with filters by period
- Per-trip score report with breakdown and export
- Score timeline chart mapped to GPS trace
- Top risky behaviors for the fleet
- REST API returning score and breakdown by vehicle or trip

### Core problem to solve
The scoring logic must be:
- explainable
- stable across trips
- fair across contexts such as highway vs urban driving
- auditable when a driver disputes a deduction

### What judges will likely care about
- Clear risk weighting logic
- Consistent score breakdown
- Human-readable explanations
- Trend views that help managers act, not just inspect

### Fast MVP
- Rule-based scoring with normalized weights
- Event extraction from telemetry thresholds
- DMS signal integration as penalties or confidence modifiers
- Dashboard showing leaderboard and event timeline

## Challenge 2: Vision-Based Collision Risk Monitor

### Goal
Estimate continuous **Time-To-Collision (TTC)** from road-facing video plus telemetry, then surface high-risk events.

### Inputs
- Road-facing video: vehicle, pedestrian, obstacle detection
- Telemetry: ego speed, brake state, steering angle
- Driver-facing video: drowsiness or non-drowsiness signal

### Required outputs
- TTC stream log per frame with timestamp and confidence
- Collision risk event list with evidence clips and severity
- Fleet risk dashboard with near-miss breakdowns
- Per-trip risk summary report
- Annotated video export with TTC overlay

### Core problem to solve
This challenge is not only about detection. It is about **reliable severity estimation** while keeping false alarms low.

### What judges will likely care about
- Sensible TTC estimation approach without radar
- Event smoothing and de-noising
- Confidence handling and alert thresholds
- Usable evidence for each near-miss event

### Fast MVP
- Use monocular distance proxy or tracked bounding-box scale change
- Fuse with ego speed to estimate relative closing risk
- Smooth TTC over time and suppress flicker
- Trigger event windows around threshold crossings

## Challenge 3: Driver Intelligence Platform

### Goal
Fuse DMS, road risk, and vehicle events into one fleet intelligence platform for remote monitoring.

### Inputs
- Driver-facing stream
- Road-facing stream and full telemetry
- Telemetry simulator signals such as speed, brake state, steering angle

### Required outputs
- Live fleet map dashboard with risk states
- Driver behavior analytics panel
- Unified risk score per trip with explainability
- Fleet-level alert log
- Post-trip coaching report
- Integration architecture diagram

### Core problem to solve
This is a systems integration challenge:
- asynchronous signals
- dashboard scale
- unified scoring logic
- actionable explanations without exposing raw model complexity

### What judges will likely care about
- End-to-end product thinking
- cross-signal fusion quality
- clarity of the remote operations workflow
- a polished non-engineer dashboard

### Fast MVP
- Reuse outputs from Challenge 1 and 2
- Build a unified event schema
- Compute a fused trip risk score
- Present a single trip drill-down with behavior plus risk evidence

## Recommendation

### Best judging strategy
Use **Challenge 3 as the umbrella pitch** but implement it through a staged delivery:

1. Complete a reliable scoring pipeline from Challenge 1
2. Complete a reliable TTC / near-miss pipeline from Challenge 2
3. Fuse them into a single dashboard and unified report for Challenge 3

### Why this is the strongest path
- It reduces execution risk.
- It keeps every subsystem demoable on its own.
- It tells a product story that judges can immediately understand.
- It creates room for bonus work such as in-car alerts or coaching messages.

## Suggested judging narrative

"We built a remote fleet intelligence layer that converts raw telemetry and video into explainable driver score, near-miss detection, and coaching insights. Fleet managers can rank drivers, inspect evidence, and act on risk in near real time."
