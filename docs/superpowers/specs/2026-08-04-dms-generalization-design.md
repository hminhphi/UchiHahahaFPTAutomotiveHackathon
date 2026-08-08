# DMS Generalization Upgrade

## Goal

Make FleetIQ's DMS training credible beyond its six supplied subjects by adding
subject-held-out evaluation and an optional local DMD RGB dataset adapter.

## Output Taxonomy

Training and deployment use four states:

| Output | Source labels |
| --- | --- |
| `attentive` | `alert`, normal/attentive DMD labels |
| `distracted` | supplied `distracted`, DMD distraction and gaze-away labels |
| `drowsy` | supplied `drowsy`, `yawning`, `microsleep`, DMD fatigue labels |
| `unknown` | inference-only rejection state; never a training label |

## Dataset Scope

The existing six trips remain a smoke-test source. Their `nthu_subject_id`
values define subject groups and must never occur in both train and validation.

DMD is supported only after the user obtains it and places RGB extracts below
`data/DMD/`. No download code, credentials, or licensed data is committed.
The adapter reads a committed manifest at `artifacts/training/dms/dmd_manifest.csv`
when present. It requires `image_path`, `subject_id`, and `label` columns.

## Model

Replace the current landmark-only five-way model with a compact four-way
multimodal classifier:

1. A frozen pretrained `timm` image encoder produces one embedding per driver frame.
2. The existing 18 landmark features are concatenated with that embedding.
3. A single bidirectional GRU classifies a temporal window.
4. Confidence below a fixed threshold maps to `unknown` only during inference.

`timm` is already pinned in the workspace lockfile and is added to the DMS
training package rather than introducing another model stack. The encoder
remains frozen for the MVP to avoid overfitting the small local
dataset and to keep MPS/CPU training practical. Fine-tuning is deferred until
the DMD validation split proves it helps.

## Evaluation

Use group-aware splits by `subject_id`; no frame, window, or trip from a held
out subject can appear in training. Report four-state macro-F1, per-class
support, confusion matrix, and transition rate per minute. The existing
within-trip temporal split is retained only for notebook demonstration, not
as the generalization metric.

## Error Handling

The DMD workflow exits with a clear message if `data/DMD/` or its manifest is
absent. The existing training workflow remains runnable without DMD.

## Non-goals

No automatic dataset download, commercial use of DMD, production-worker
changes, cloud training, or model fine-tuning in this increment.
