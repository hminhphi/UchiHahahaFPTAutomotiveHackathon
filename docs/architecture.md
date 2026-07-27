# Initial System Architecture

## Product idea
A remote fleet intelligence system that ingests simulator telemetry and optional vision signals, produces explainable trip scores and risk events, and exposes them in a fleet manager dashboard.

## Recommended module split

### 1. Ingestion
- Trip metadata
- Telemetry stream or batch upload
- Driver-facing event stream
- Road-facing event stream

### 2. Feature extraction
- Hard brake, harsh steering, speeding, lane offset statistics
- Driver state segments such as attentive, distracted, drowsy
- Road risk segments such as lead vehicle too close, lane departure, obstacle ahead

### 3. Event engine
- Standardized event schema
- Severity scoring
- Timestamp alignment
- Evidence window generation

### 4. Scoring engine
- Behavior score
- Vehicle handling score
- Collision risk score
- Unified trip score with explainability

### 5. APIs
- Trip summary endpoint
- Driver ranking endpoint
- Event log endpoint
- Fleet analytics endpoint

### 6. Dashboard
- Fleet overview
- Driver leaderboard
- Trip drill-down
- Risk timeline
- Evidence panel
- Coaching report view

## Canonical event schema

Each event should include:
- event_id
- trip_id
- vehicle_id
- driver_id
- timestamp_start
- timestamp_end
- source such as telemetry, dms, road_vision, fused
- event_type such as harsh_brake, distraction, lane_departure, near_miss
- severity from 1 to 5
- confidence from 0 to 1
- explanation
- evidence_uri

## MVP data flow

1. Read telemetry CSV or simulator output
2. Read precomputed vision events or lightweight model outputs
3. Align everything on a shared trip timeline
4. Generate normalized events
5. Score the trip
6. Store outputs as JSON for dashboard consumption

## Scoring strategy for demo

Start rule-based, then optionally add learned calibration.

Suggested top-level score formula:

- 40 percent driver behavior
- 30 percent vehicle handling
- 30 percent collision risk

Each category can start at 100 and lose points based on event severity and duration. Use context normalization where possible, such as different speeding tolerance for highway and urban segments.

## Demo goal
The best hackathon demo is likely not the most complex model. It is the one that is:
- stable
- explainable
- visually convincing
- easy for judges to interact with in under 3 minutes
