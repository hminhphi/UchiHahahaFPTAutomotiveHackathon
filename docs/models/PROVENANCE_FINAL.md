# Model And Runtime Provenance: Final Round 2

## Purpose

This document is the release authority for model roles and claims in the final
FleetIQ Guardian Round 2 build (`v1.1.2`). It prevents an offline training metric, a generated
label, and a runtime signal from being described as the same thing.

## Runtime Components

| Capability | Final implementation | Local artifact or source | Allowed claim |
| --- | --- | --- | --- |
| Road object evidence | Precomputed `label2_yolo_v3` detections filtered by bbox size and ego-corridor overlap | `artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt`; `data/.../kitti/label2_yolo_v3/` | A detected retained object is linked to its source frame |
| Distance and TTC | GT-depth ROI on retained objects; previous keyframe fallback for sparse depth | `data/.../kitti/depth/`; `artifacts/trips/<trip>/analysis/road/` | Explainable depth-based TTC proxy, not learned depth or ground truth evaluation |
| DMS state | MediaPipe Face Landmarker geometry: EAR, MAR, pose, PERCLOS, 15-frame smoothing | `artifacts/models/dms/face_landmarker.task`; `ml/training/dms/src/fleetiq_training_dms/` | State evidence and consolidated event windows |
| DMS checkpoint | Offline two-stage sequence training artifact | `artifacts/models/dms/best_sequence_model.pt` | Training artifact only; not the final dashboard runtime |
| Fusion score | Deterministic `RiskScorer` plus event/coaching mapping | `services/fusion-worker/src/fleetiq_fusion/scoring.py`; `artifacts/trips/<trip>/analysis/fusion/` | Reproducible trip-level evidence score |

## DMS Event Policy

1. Runtime state features use a 15-frame rolling window.
2. A DMS state must be continuous for at least 15 frames before it becomes an event.
3. A repeat of the same state within 100 frames (five seconds at 20 FPS) extends the existing event, even if another valid state appears briefly between observations.
4. A different stable state remains a distinct event.

The final all-trip regeneration produced 61 consolidated DMS windows across
T01d-T10d. Every retained window is at least 15 frames.

## Metric Policy

The repository contains historical checkpoint evaluation documents with
inconsistent metric values. The final build intentionally does not present either value as a
runtime, redacted-trip, or organizer-evaluated result. Publish a new metric only
with its immutable evaluation artifact, dataset/split definition, checkpoint
hash, evaluation command, and commit ID.

## Distribution Policy

- Source code and this provenance record may be public.
- Organizer data, model weights, MediaPipe task files, generated trip media,
  predictions, and derived evidence are private reviewer artifacts unless the
  organizer explicitly approves redistribution.
- The private runtime handoff must include hashes for every packaged file.
