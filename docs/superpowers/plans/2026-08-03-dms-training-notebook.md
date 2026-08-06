# DMS Training Visualization Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one executable notebook that visualizes and runs the existing DMS training pipeline.

**Architecture:** The notebook imports the current DMS package instead of copying its extractor, dataloader, or Bi-LSTM. It adds presentation and training-loop cells around those existing boundaries, retaining the configured data paths, hyperparameters, `Config.EPOCHS`, and checkpoint format.

**Tech Stack:** Python 3.12, Jupyter notebook JSON, PyTorch, pandas, matplotlib, scikit-learn, existing FleetIQ DMS package.

## Global Constraints

- Create only `ml/notebooks/04_dms_training_visualization.ipynb`.
- Use `Config.EPOCHS` exactly; do not introduce notebook-specific epoch settings.
- Select CUDA, then MPS, then CPU in notebook setup.
- Reuse `extract_all_and_save`, `get_temporal_block_dataloaders`, `FEATURE_COLS`, and `build_sequence_model`.
- Use the existing `artifacts/models/dms/best_sequence_model.pt` checkpoint location and payload fields.
- Add no dependencies and do not change production training code.

---

### Task 1: Create the DMS training notebook

**Files:**
- Create: `ml/notebooks/04_dms_training_visualization.ipynb`

**Interfaces:**
- Consumes: `Config`, `extract_all_and_save()`, `get_temporal_block_dataloaders(feature_dir, trip_ids, seq_len, batch_size, train_ratio)`, `FEATURE_COLS`, `build_sequence_model(...)`.
- Produces: `artifacts/training/dms/extracted_features/<trip>_features.csv` and `artifacts/models/dms/best_sequence_model.pt`.

- [ ] **Step 1: Write the failing notebook inspection check**

Run:

```bash
python -c "from pathlib import Path; assert Path('ml/notebooks/04_dms_training_visualization.ipynb').exists()"
```

Expected: FAIL with `AssertionError` because the notebook does not exist.

- [ ] **Step 2: Create the notebook with ordered cells**

Create notebook sections titled:

```text
FleetIQ DMS Training: End-to-End Visual Walkthrough
1. Setup and configured device
2. Dataset readiness
3. Extract and inspect 18 features
4. Build temporal dataloaders
5. Train the Bi-LSTM
6. Validate and inspect predictions
```

The setup cell must use:

```python
DEVICE = (
    "cuda" if torch.cuda.is_available()
    else "mps" if torch.backends.mps.is_available()
    else "cpu"
)
```

The training cell must loop with:

```python
for epoch in range(1, Config.EPOCHS + 1):
```

and save the existing checkpoint keys: `epoch`, `model_state_dict`, `val_acc`, `seq_len`, `feature_dim`, `mean_scaler`, and `std_scaler`.

- [ ] **Step 3: Run the inspection check**

Run:

```bash
python -c "import json; p='ml/notebooks/04_dms_training_visualization.ipynb'; n=json.load(open(p)); s='\n'.join(''.join(c.get('source', [])) for c in n['cells']); assert 'Config.EPOCHS' in s; assert 'extract_all_and_save' in s; assert 'get_temporal_block_dataloaders' in s; assert 'build_sequence_model' in s; assert 'class DriverSequenceModel' not in s"
```

Expected: PASS.

- [ ] **Step 4: Validate notebook JSON and Python syntax**

Run:

```bash
python -c "import json; p='ml/notebooks/04_dms_training_visualization.ipynb'; n=json.load(open(p)); assert n['nbformat'] == 4; [compile(''.join(c.get('source', [])), f'{p}:{i}', 'exec') for i, c in enumerate(n['cells']) if c['cell_type'] == 'code']"
```

Expected: PASS.

- [ ] **Step 5: Review diff**

Run:

```bash
git diff --check -- ml/notebooks/04_dms_training_visualization.ipynb
```

Expected: PASS with no whitespace errors.
