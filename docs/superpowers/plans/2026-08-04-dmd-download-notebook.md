# DMD Download and Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a user-authorized DMD archive downloader and an optional DMD section to the DMS training notebook.

**Architecture:** A standard-library CLI accepts user-supplied official DMD archive URLs, stores archives under the ignored local data directory, validates optional checksums, and extracts only safe archive members. The notebook remains self-contained for supplied data and treats DMD as an optional external-data extension.

**Tech Stack:** Python 3.12 standard library, pytest, Jupyter notebook JSON.

## Global Constraints

- Do not automate consent, scrape the DMD portal, embed access tokens, or bypass DMD terms.
- Accept only explicit HTTP(S) `--url` values supplied by a user who accepted DMD terms.
- Extract only below `data/DMD/`; reject archive path traversal.
- DMD absence must not stop the supplied-trip notebook walkthrough.

---

### Task 1: Add safe user-authorized DMD downloader

**Files:**
- Create: `tools/dataset/download_dmd.py`
- Create: `tools/dataset/test_download_dmd.py`

**Interfaces:**
- Produces: `download(url: str, destination: Path, expected_sha256: str | None) -> Path` and `extract(archive: Path, destination: Path) -> None`.
- CLI: `python tools/dataset/download_dmd.py --url <official-url> [--sha256 <digest>]`.

- [ ] **Step 1: Write failing safety tests**

```python
from pathlib import Path
import pytest
from tools.dataset.download_dmd import safe_member_path, validate_url


def test_rejects_non_http_download_urls():
    with pytest.raises(ValueError, match="HTTP"):
        validate_url("file:///tmp/dmd.zip")


def test_rejects_archive_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        safe_member_path(tmp_path, "../../outside.txt")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run --group dev pytest tools/dataset/test_download_dmd.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement downloader with stdlib only**

Use `urllib.request.urlretrieve` or streamed `urlopen` for HTTP(S) download,
`hashlib.sha256` for supplied digest verification, `zipfile` and `tarfile` for
extraction, and `Path.resolve().is_relative_to(destination.resolve())` before
extracting every member. Reject unsupported file suffixes and expose `--output`
defaulting to `data/DMD`.

- [ ] **Step 4: Run downloader tests to verify pass**

Run: `uv run --group dev pytest tools/dataset/test_download_dmd.py -v`

Expected: PASS.

### Task 2: Add optional DMD walkthrough to the notebook

**Files:**
- Modify: `ml/notebooks/04_dms_training_visualization.ipynb`

**Interfaces:**
- Consumes: optional `data/DMD/` and `artifacts/training/dms/dmd_manifest.csv`.
- Produces: DMD coverage preview and an MPS training command for `fleetiq-train-dms-generalized`.

- [ ] **Step 1: Add the optional DMD markdown and code cells**

Add a final section titled `## 7. Optional DMD generalization training`. It must
show a user-supplied URL command, check for the optional manifest, summarize
`subject_id` and `label` coverage when present, and print:

```python
print(
    "uv run --package fleetiq-training-dms fleetiq-train-dms-generalized "
    "--manifest artifacts/training/dms/dmd_manifest.csv "
    "--validation-subject <subject_id> --device mps"
)
```

- [ ] **Step 2: Validate notebook structure and syntax**

Run:

```bash
python -c "import json; p='ml/notebooks/04_dms_training_visualization.ipynb'; n=json.load(open(p)); s='\n'.join(''.join(c.get('source', [])) for c in n['cells']); assert 'Optional DMD generalization training' in s; assert 'fleetiq-train-dms-generalized' in s; [compile(''.join(c.get('source', [])), f'{p}:{i}', 'exec') for i, c in enumerate(n['cells']) if c['cell_type'] == 'code']"
```

Expected: PASS.

- [ ] **Step 3: Run focused and full verification**

Run:

```bash
uv run --group dev pytest tools/dataset/test_download_dmd.py -v
uv run --group dev pytest -q
git diff --check
```

Expected: PASS.
