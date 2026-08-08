# DMS Notebook Phone-Use Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional phone-use inference and visual inspection to the existing DMS training notebook.

**Architecture:** Reuse `PhoneUseDetector` and `PhoneUseSmoother` directly in one optional notebook cell. A second cell visualizes the in-memory result or falls back to the existing trip prediction CSV, so visualization still works when YOLO is unavailable.

**Tech Stack:** Jupyter Notebook, Python, pandas, matplotlib, Pillow, existing FleetIQ DMS modules.

---

### Task 1: Add optional phone-use inference

**Files:**
- Modify: `ml/notebooks/04_dms_training_visualization.ipynb`

- [ ] **Step 1: Add a phone-use section after validation**

Add a markdown cell titled `## 7. Optional phone-use detection and visualization`, explaining that `phone_use` is independent from the broad driver-state class.

- [ ] **Step 2: Add a guarded detector cell**

The cell imports `PhoneUseDetector` and `PhoneUseSmoother`, selects `T01-Sample`, and initializes:

```python
PHONE_TRIP_ID = "T01-Sample"
PHONE_MODEL = REPO_ROOT / "yolo11n.pt"
PHONE_CONFIDENCE = 0.40
phone_results = None
```

If the model exists, iterate sorted `driver/*.jpg` frames, parse each frame id,
call the existing detector, smooth each result, and build a DataFrame with
`frame_id`, `phone_use`, and `image_path`. Catch detector initialization errors
and print the existing setup command:

```bash
uv run --with ultralytics python -c 'from ultralytics import YOLO; YOLO("yolo11n.pt")'
```

- [ ] **Step 3: Add CSV fallback and charts**

Use `phone_results` when available. Otherwise read
`artifacts/predictions/dms/T01-Sample_twostage.csv`, attach driver image paths,
and normalize `phone_use` values to nullable booleans. Display:

```python
display(phone_view["phone_use"].value_counts(dropna=False).rename("frames").to_frame())
ax.step(phone_view["frame_id"], phone_view["phone_use"].map({True: 1, False: 0}), where="post")
```

Then show up to three `phone_use == True` driver frames with Pillow and
Matplotlib. If neither inference nor CSV data exists, print the documented
prediction command instead of raising.

- [ ] **Step 4: Renumber the existing DMD section to section 8**

Change only its markdown heading; leave its existing code untouched.

### Task 2: Validate notebook structure

**Files:**
- Verify: `ml/notebooks/04_dms_training_visualization.ipynb`

- [ ] **Step 1: Validate JSON and notebook cell structure**

Run:

```bash
jq empty ml/notebooks/04_dms_training_visualization.ipynb
uv run python -c 'import json; from pathlib import Path; notebook=json.loads(Path("ml/notebooks/04_dms_training_visualization.ipynb").read_text()); assert notebook["nbformat"] == 4; assert any("Optional phone-use detection" in "".join(cell.get("source", [])) for cell in notebook["cells"])'
```

Expected: both commands exit 0.

- [ ] **Step 2: Compile every code cell**

Run:

```bash
uv run python -c 'import json; from pathlib import Path; notebook=json.loads(Path("ml/notebooks/04_dms_training_visualization.ipynb").read_text()); [compile("".join(cell.get("source", [])), f"cell-{index}", "exec") for index, cell in enumerate(notebook["cells"]) if cell["cell_type"] == "code"]'
```

Expected: exit 0 with no syntax errors.

- [ ] **Step 3: Preserve the user's staged notebook ownership**

Do not commit the notebook automatically because it was already staged before
this task. Report the verified modification for the user to review and commit
with their other notebook work.
