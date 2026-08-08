# Driver Dataset Downloader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one registry-driven CLI that downloads user-authorized driver-behavior datasets through the existing safe archive helper.

**Architecture:** `download_driver_datasets.py` declares the five supported datasets and their official landing pages, parses dataset-keyed direct URLs, and delegates transfer/extraction to `download_dmd.py`. The notebook directs users to the new `--list` and `--dataset` commands.

**Tech Stack:** Python 3.12 standard library, pytest, existing dataset downloader, Jupyter notebook JSON.

## Global Constraints

- No portal scraping, login automation, access-token handling, or license bypass.
- URLs must be explicit and supplied by the user after accepting the dataset's terms.
- Reuse `download`, `extract`, and archive safety checks from `download_dmd.py`.
- Write data only below `data/external/<dataset>/`.

---

### Task 1: Add registry CLI and tests

**Files:**
- Create: `tools/dataset/download_driver_datasets.py`
- Create: `tools/dataset/test_download_driver_datasets.py`

**Interfaces:**
- Produces: `DATASETS`, `parse_dataset_urls(values: list[str]) -> dict[str, str]`, and `main()`.
- CLI: `--list`, `--dataset {all,dmd,uta-rldd,yawdd,nthu-ddd,auc}`, and repeatable `--url dataset=url`.

- [ ] **Step 1: Write failing registry tests**

```python
import pytest
from tools.dataset.download_driver_datasets import parse_dataset_urls


def test_parses_dataset_keyed_urls():
    assert parse_dataset_urls(["yawdd=https://example.test/yawdd.zip"]) == {
        "yawdd": "https://example.test/yawdd.zip"
    }


def test_rejects_unknown_dataset_key():
    with pytest.raises(ValueError, match="Unknown dataset"):
        parse_dataset_urls(["unknown=https://example.test/archive.zip"])
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run --group dev pytest tools/dataset/test_download_driver_datasets.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the minimal registry wrapper**

Declare `dmd`, `uta-rldd`, `yawdd`, `nthu-ddd`, and `auc` with official
landing-page URLs and access notes. `--list` prints each entry without network
access. For requested datasets with a supplied direct URL, call the existing
safe `download()` and `extract()` functions into `data/external/<dataset>/`.
For missing URLs, print the official page and access note then continue.

- [ ] **Step 4: Run registry tests to verify pass**

Run: `uv run --group dev pytest tools/dataset/test_download_driver_datasets.py -v`

Expected: PASS.

### Task 2: Update DMS notebook commands

**Files:**
- Modify: `ml/notebooks/04_dms_training_visualization.ipynb`

**Interfaces:**
- Consumes: `tools/dataset/download_driver_datasets.py`.
- Produces: visible `--list` and direct-URL download examples.

- [ ] **Step 1: Replace the DMD-only command in the optional section**

The notebook must display:

```python
print("python tools/dataset/download_driver_datasets.py --list")
print("python tools/dataset/download_driver_datasets.py --dataset yawdd --url yawdd=<official-archive-url>")
```

- [ ] **Step 2: Validate notebook and all tests**

Run:

```bash
python -c "import json; p='ml/notebooks/04_dms_training_visualization.ipynb'; n=json.load(open(p)); s='\n'.join(''.join(c.get('source', [])) for c in n['cells']); assert 'download_driver_datasets.py --list' in s; [compile(''.join(c.get('source', [])), f'{p}:{i}', 'exec') for i, c in enumerate(n['cells']) if c['cell_type'] == 'code']"
uv run --group dev pytest tools/dataset/test_download_dmd.py tools/dataset/test_download_driver_datasets.py -v
uv run --group dev pytest -q
git diff --check
```

Expected: PASS.
