# DMS Generalization Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add subject-held-out four-state DMS training using optional DMD RGB records and a frozen `timm` image encoder fused with the existing landmark features.

**Architecture:** Keep the existing five-state Bi-LSTM pipeline untouched for the supplied demo. Add a generalization path that maps raw labels to four training classes, builds subject-grouped frame windows from local manifests, fuses frozen frame embeddings with 18 landmark features, and reports held-out-subject metrics.

**Tech Stack:** Python 3.12, PyTorch, timm, pandas, scikit-learn, Pillow, existing FleetIQ DMS training package.

## Global Constraints

- DMD stays optional and local below `data/DMD/`; do not download or commit DMD data.
- DMD manifests require `image_path`, `subject_id`, and `label` columns.
- Output classes are `attentive`, `distracted`, and `drowsy`; `unknown` is inference-only.
- Every split is grouped by subject ID; one subject cannot occur in train and validation.
- The image encoder is frozen for this increment.
- Reuse workspace-pinned `timm`; do not add a second image-model dependency.
- Do not change production workers or the existing five-state trainer.

---

### Task 1: Add shared taxonomy and subject-safe manifests

**Files:**
- Create: `ml/training/dms/src/fleetiq_training_dms/generalization_data.py`
- Create: `ml/training/dms/tests/test_generalization_data.py`

**Interfaces:**
- Produces: `normalize_label(raw_label: str) -> int | None`, `load_manifest(path: Path) -> pd.DataFrame`, and `subject_split(records: pd.DataFrame, validation_subject: str) -> tuple[pd.DataFrame, pd.DataFrame]`.
- Consumes: manifests with `image_path`, `subject_id`, and `label`.

- [ ] **Step 1: Write failing taxonomy and subject-leakage tests**

```python
from pathlib import Path
import pandas as pd
from fleetiq_training_dms.generalization_data import normalize_label, subject_split


def test_normalizes_five_source_states_to_three_training_classes():
    assert normalize_label("alert") == 0
    assert normalize_label("texting") == 1
    assert normalize_label("microsleep") == 2
    assert normalize_label("unknown") is None


def test_subject_split_never_shares_a_subject():
    records = pd.DataFrame({"subject_id": ["1", "1", "2"], "label": [0, 0, 1]})
    train, validation = subject_split(records, validation_subject="2")
    assert set(train.subject_id) == {"1"}
    assert set(validation.subject_id) == {"2"}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_generalization_data.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'fleetiq_training_dms.generalization_data'`.

- [ ] **Step 3: Implement the minimal manifest helpers**

```python
CLASS_NAMES = ("attentive", "distracted", "drowsy")

def normalize_label(raw_label: str) -> int | None:
    label = raw_label.strip().lower()
    if label in {"alert", "attentive", "normal"}:
        return 0
    if label in {"distracted", "texting", "phone", "gaze_away"}:
        return 1
    if label in {"drowsy", "yawning", "microsleep", "sleepy_driving"}:
        return 2
    return None
```

`load_manifest` validates required columns, resolves relative image paths from
the manifest directory, drops unmapped labels, and raises `ValueError` with
the missing column names. `subject_split` filters on `subject_id` and raises
`ValueError` when either side is empty.

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_generalization_data.py -v`

Expected: PASS.

### Task 2: Add frozen visual-landmark GRU model

**Files:**
- Modify: `ml/training/dms/pyproject.toml`
- Modify: `ml/training/dms/src/fleetiq_training_dms/model.py`
- Create: `ml/training/dms/tests/test_generalization_model.py`

**Interfaces:**
- Produces: `VisualLandmarkGRU(image_model_name: str = "mobilenetv3_small_100", feature_dim: int = 18, hidden_dim: int = 128, num_classes: int = 3) -> nn.Module`.
- Consumes: RGB frame tensors shaped `[batch, sequence, 3, height, width]` and landmark tensors shaped `[batch, sequence, 18]`.

- [ ] **Step 1: Write the failing model contract test**

```python
import torch
from fleetiq_training_dms.model import VisualLandmarkGRU


def test_visual_landmark_gru_outputs_three_logits_per_window():
    model = VisualLandmarkGRU(pretrained=False)
    images = torch.zeros(2, 4, 3, 64, 64)
    landmarks = torch.zeros(2, 4, 18)
    assert model(images, landmarks).shape == (2, 3)
    assert not any(parameter.requires_grad for parameter in model.encoder.parameters())
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_generalization_model.py -v`

Expected: FAIL because `VisualLandmarkGRU` is not defined.

- [ ] **Step 3: Add the existing pinned encoder dependency and minimal model**

Add `timm>=1.0.11` to the DMS package dependencies. Implement the model with
`timm.create_model(image_model_name, pretrained=pretrained, num_classes=0,
global_pool="avg")`, set every encoder parameter's `requires_grad` to `False`,
concatenate frame embeddings with landmark features, run `nn.GRU(...,
bidirectional=True, batch_first=True)`, and classify the final time step.

- [ ] **Step 4: Run test to verify pass**

Run: `uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_generalization_model.py -v`

Expected: PASS.

### Task 3: Add grouped training and evaluation entry point

**Files:**
- Create: `ml/training/dms/src/fleetiq_training_dms/train_generalized.py`
- Modify: `ml/training/dms/pyproject.toml`
- Create: `ml/training/dms/tests/test_train_generalized.py`

**Interfaces:**
- Produces: `fleetiq-train-dms-generalized --manifest <path> --validation-subject <id>`.
- Consumes: a validated manifest; optional landmark CSV columns matching `FEATURE_COLS`.
- Produces: `artifacts/models/dms/generalized_best.pt` and a JSON metrics report beside it.

- [ ] **Step 1: Write the failing CLI validation test**

```python
import pytest
from fleetiq_training_dms.train_generalized import parse_args


def test_training_cli_requires_manifest_and_validation_subject(monkeypatch):
    monkeypatch.setattr("sys.argv", ["fleetiq-train-dms-generalized"])
    with pytest.raises(SystemExit):
        parse_args()
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_train_generalized.py -v`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the minimal training path**

The CLI must require `--manifest` and `--validation-subject`, default to
`--epochs Config.EPOCHS`, and reject a missing DMD manifest with
`FileNotFoundError`. Build temporal windows only inside each subject, create
train/validation records via `subject_split`, train the frozen encoder + GRU,
save the best validation checkpoint, and write JSON with `macro_f1`,
`class_support`, `validation_subject`, and `class_names`.

Add this project script:

```toml
fleetiq-train-dms-generalized = "fleetiq_training_dms.train_generalized:main"
```

- [ ] **Step 4: Run focused tests and the full suite**

Run:

```bash
uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_generalization_data.py ml/training/dms/tests/test_generalization_model.py ml/training/dms/tests/test_train_generalized.py -v
uv run --group dev pytest -q
```

Expected: PASS.
