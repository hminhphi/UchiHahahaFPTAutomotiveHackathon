# DMS Notebook Phone-Use Visualization Design

## Goal

Extend the DMS training visualization notebook with an optional phone-use
detection run and a visual review of its results.

## Flow

1. A new optional section selects `T01-Sample`, creates the existing
   `PhoneUseDetector` and `PhoneUseSmoother`, and evaluates its driver frames.
2. If Ultralytics or `yolo11n.pt` is unavailable, the section prints the
   existing model-preparation command and does not block the rest of the
   notebook.
3. The visualization uses the in-memory detection results when that cell ran;
   otherwise it reads the existing `artifacts/predictions/dms/<trip>_twostage.csv`.
4. It shows positive/negative/unavailable counts, a frame-level phone-use
   timeline, and up to three driver-frame examples of detected phone use.

## Boundaries

The notebook reuses the production detector and 3-of-5 smoother. It does not
train a second phone model or change the prediction CSV schema.

## Verification

Validate notebook JSON and execute a small import/compilation check of the
new cells. The optional detector is guarded so no model download is required.
