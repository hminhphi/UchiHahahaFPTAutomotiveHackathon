# DMS Training Visualization Notebook

## Goal

Add one runnable notebook at `ml/notebooks/04_dms_training_visualization.ipynb`
that makes the existing DMS training pipeline observable without creating a
second implementation of it.

## Scope

The notebook will:

- import the existing DMS configuration, feature extractor, dataloaders, and
  Bi-LSTM model;
- choose CUDA, MPS, then CPU for notebook execution;
- validate the configured dataset location and show the active training
  configuration, including `Config.EPOCHS`;
- extract features, visualize class balance and feature distributions, and
  inspect one temporal sequence batch;
- train with the existing hyperparameters for exactly `Config.EPOCHS` epochs;
- save the best checkpoint at the established DMS checkpoint location;
- visualize train/validation history, a validation confusion matrix, and a
  small set of predictions.

## Data Flow

`Config` defines data and artifact paths. `extract_all_and_save()` produces the
existing feature CSVs. `get_temporal_block_dataloaders()` creates the temporal
train/validation split. The existing `build_sequence_model()` model is trained
inside notebook cells and writes the same checkpoint shape used by evaluation
and prediction.

## Error Handling

Before extraction, the notebook will raise a clear error when the configured
dataset root or its configured trips are absent. It will state that feature
extraction downloads the MediaPipe face-landmarker asset when it is missing.

## Verification

The notebook must be valid `.ipynb` JSON. A small notebook inspection check
will confirm that it uses `Config.EPOCHS`, the existing pipeline functions,
and no copied model definition. Full training is run by the user because it
depends on the local dataset and hardware.

## Non-goals

No changes to training behavior, hyperparameters, labels, checkpoint format,
or production workers. No new dependencies and no separate notebook-only
training module.
