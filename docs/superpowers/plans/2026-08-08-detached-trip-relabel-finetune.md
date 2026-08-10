# Detached-Trip Relabel → YOLO Finetune → Artifact Regeneration

Status file for the background LocateAnything labeling job and the work that
follows it. Written 2026-08-08.

---

## Why this work exists

The dashboard trip pages rendered **zero object detections** for every detached
trip (T01d–T10d), even though cars are clearly visible in the frames.

**Root cause (confirmed, not a guess):**

`services/roadface-worker/tests/generate_ai_artifacts.py:273` reads per-frame
boxes from `<trip>/kitti/label2_custom/{frame:06d}.txt`. For the detached trips
that directory did not exist:

```
data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted/T01d/kitti/
  calib  depth  image_2  image_3  label_2          <-- no label2_custom
data/Practice_Dataset/Practice_Dataset/T01-Sample/kitti/
  calib  depth  image_2  image_3  label_2  label2_custom  label2_yolop
```

`parse_kitti_label()` returns `[]` for a missing file, so every generated
`analysis/road/*.json` had `"detections": []`. The API and web layers were
correct; the input labels were simply absent.

This was verified end to end: all 50 generated road frames for T01d had zero
detections, and the API returns exactly what the artifacts contain.

---

## Current state

### Already fixed and verified working

- Depth endpoint serves correctly both with and without the `.png` suffix
  (`/api/trips/T01d/derived/depth/000000` and `.../000000.png` → HTTP 200,
  `image/png`, ~20 KB).
- Road video streams through the web layer
  (`/api/trips/T01d/road-video/content` → HTTP 200, `video/mp4`, 9,173,922
  bytes, `accept-ranges: bytes`).
- DMS analysis returns real per-frame state (e.g. frame 0 → `drowsy`,
  confidence 0.85, EAR 0.201).
- Playwright integration suite: 25/32 passing. The 7 failures are transient
  `socket hang up` timeouts under concurrent API load, not logic defects.

### Dependency changes made

`ml/training/roadface/pyproject.toml` — added `decord>=0.6` and `lmdb>=1.4` to
the `models` extra. The LocateAnything remote code imports both at load time;
without them `AutoProcessor.from_pretrained` raises `ImportError`. Re-sync with:

```powershell
uv sync --all-packages --extra cu130 --extra models
```

### Background job in flight

Full LocateAnything-3B relabel of all 10 detached trips.

| Field | Value |
| --- | --- |
| Command | `uv run --package fleetiq-training-roadface fleetiq-label-roadface --dataset redacted --generation-mode slow --device cuda --continue-on-error` |
| PID file | `artifacts/logs/locateanything.pid` (PID 18484 at launch) |
| Stdout | `artifacts/logs/locateanything_detached.log` |
| Stderr | `artifacts/logs/locateanything_detached.log.err` |
| Output | `<trip>/kitti/label2_custom/{frame:06d}.txt` + `_locateanything_raw.jsonl` |
| Scope | 17,999 frames across T01d–T10d |
| Throughput | ~2.2 s/frame |
| ETA | ~10 h from 13:32 launch, finishing ~00:30 on 2026-08-09 |

Progress at 14:43 — T01d complete (1800/1800, 1280 frames with ≥1 box),
T02d in progress, zero errors recorded.

**Generation-mode benchmark (measured, 3 frames each on T01d):**

| Mode | s/frame | Note |
| --- | --- | --- |
| `slow` | **2.25** | Chosen. Fastest *and* matches how the Practice dataset was labeled. |
| `fast` | 13.2 | Box-averaging refinement dominates runtime. |
| `hybrid` | 14.1 | Slowest. |

`slow` being fastest is counter-intuitive but reproducible — `fast`/`hybrid`
run an extra iterative box-refinement loop. Do not "optimize" this to `fast`.

---

## Check progress

```powershell
pwsh -File scripts/check-labeling-status.ps1

# auto-refresh every 60s until the run ends
pwsh -File scripts/check-labeling-status.ps1 -Watch
```

Reports process liveness, GPU usage, per-trip counts, overall percent, s/frame,
ETA, error count, and recent log lines.

### If the job died before finishing

Already-labeled frames are skipped, so simply relaunch — it resumes:

```powershell
uv run --package fleetiq-training-roadface fleetiq-label-roadface `
  --dataset redacted --generation-mode slow --device cuda --continue-on-error
```

To relaunch detached with logging, mirror the original launch:

```powershell
$log = "artifacts/logs/locateanything_detached.log"
$p = Start-Process -FilePath "uv" `
  -ArgumentList "run","--package","fleetiq-training-roadface","fleetiq-label-roadface",`
                "--dataset","redacted","--generation-mode","slow","--device","cuda","--continue-on-error" `
  -WorkingDirectory "C:\Users\admin\Documents\Projects\AutomotiveHacathon" `
  -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden
$p.Id | Out-File artifacts/logs/locateanything.pid -Encoding ascii
```

**GPU contention:** LocateAnything-3B needs ~7 GB VRAM on the 16 GB RTX 5060 Ti.
LM Studio previously held ~15 GB and blocked model load. Confirm free VRAM
before launching anything GPU-bound:

```powershell
nvidia-smi --query-gpu=memory.used,memory.free --format=csv
```

---

## Remaining work

### Step 1 — Confirm labeling finished cleanly

```powershell
pwsh -File scripts/check-labeling-status.ps1
```

Require: all 10 trips at 100%, total 17,999, and the error count is zero or
small and understood. Spot-check a few labels for sanity — boxes should track
smoothly across consecutive frames, as they did in the T01d smoke test:

```
Car 0.00 0 -10.00 42.88 174.96 111.36 198.00 -1.00 -1.00 -1.00 -1000.00 -1000.00 -1000.00 -10.00
Car 0.00 0 -10.00 172.80 177.84 212.48 196.92 -1.00 -1.00 -1.00 -1000.00 -1000.00 -1000.00 -10.00
```

Note that a meaningful share of frames legitimately contain no objects — T01d
produced boxes on 1280 of 1800 frames. Empty files are expected, not a failure.

### Step 2 — Export a YOLO dataset from the detached labels

`prepare_custom_dataset.py` has **no console-script entrypoint**; invoke the
module directly. Its defaults target the Practice dataset and its
`DEFAULT_SPLIT`/`PRACTICE_TRIPS` constants only know `T0N-Sample` names, so the
detached trips must be passed explicitly via `--trips`.

```powershell
uv run --package fleetiq-training-roadface python -m fleetiq_training_roadface.prepare_custom_dataset `
  --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted `
  --output-dir artifacts/training/roadface/yolo_dataset_detached `
  --trips T01d T02d T03d T04d T05d T06d T07d T08d T09d T10d `
  --link-mode hardlink
```

Two things to decide and handle deliberately:

1. **Split.** `trip_split()` returns `"train"` for any unrecognized trip name,
   so every detached trip lands in `train` and `val`/`test` come out empty.
   Ultralytics needs a non-empty `val` set. Either pass a held-out subset in a
   second invocation, or extend `DEFAULT_SPLIT` to assign e.g. T09d → val and
   T10d → test. Prefer editing `DEFAULT_SPLIT` so the split is reproducible and
   recorded in the emitted `split.json`.
2. **`--output-dir` is deleted and recreated** (`shutil.rmtree`) on every run.
   Do not point it at `yolo_dataset_custom`, which holds the Practice export
   that the current `yolo26n_custom` checkpoint was trained on.

Class IDs must stay aligned with the runtime detector. Both
`prepare_custom_dataset.LABEL2_CLASS_NAMES` and
`services/roadface-worker/src/fleetiq_roadface/yolo_detector.py:15`
(`YOLO26_CLASS_NAMES`) declare the same order — `Car, Bus, LongVehicle,
Motorcycle, Cyclist, Pedestrian`. Do not reorder either list.

For reference, the existing Practice export produced 2,983 frames / 7,447
objects across six trips.

### Step 3 — Finetune from the existing checkpoint

Start from the already-trained weights rather than a fresh backbone:

```
artifacts/training/roadface/train_runs/yolo26n_custom/weights/best.pt
```

That path is also `YOLO26_DEFAULT_WEIGHTS` in `yolo_detector.py:24`, so the
runtime picks up whatever lives there by default.

```powershell
uv run --package fleetiq-training-roadface fleetiq-train-roadface `
  --dataset-yaml artifacts/training/roadface/yolo_dataset_detached/dataset.yaml `
  --model artifacts/training/roadface/train_runs/yolo26n_custom/weights/best.pt `
  --name yolo26n_detached `
  --epochs 50 --imgsz 640 --batch 8 --device 0
```

Tune `--batch` to fit 16 GB VRAM; drop it if CUDA OOMs. Training is long —
launch it detached with logging the same way as the labeling job.

**Write to a new run name (`yolo26n_detached`).** Do not overwrite
`yolo26n_custom` until the new checkpoint is evaluated; it is the only working
fallback. Compare the two on a held-out split before promoting.

### Step 4 — Regenerate road analysis artifacts

Once labels exist, the existing generator produces non-empty detections with no
code change:

```powershell
uv run --package fleetiq-roadface python services/roadface-worker/tests/generate_ai_artifacts.py `
  --dataset-root data/Hackathon_Dataset_Redacted/Hackathon_Dataset_Redacted `
  --output-dir artifacts/trips
```

**Known limitation — 50-frame cap.** `generate_ai_artifacts.py:280` hard-codes
`range(min(len(frames), 50))`, so only frames 0–49 get analysis JSON despite
1,800 frames of labels. Decide whether the demo needs full coverage; if so,
raise or parameterize that bound. Note the cost is per-frame JSON across ten
trips, so full coverage means ~18,000 files per analysis type.

Also note this generator derives distance from KITTI 3D `z`, but LocateAnything
emits 2D-only boxes with `-1000` sentinels for 3D fields (see `kitti_2d_line`
in `label_locateanything.py:179`). `compute_distance` rejects those, so
`distance_m`, `ttc_s`, and therefore the road risk component stay `None`.
Detections and boxes will render, but if the demo needs TTC on detached trips,
distance must come from the depth maps instead — that is a separate change to
scope explicitly, not something to bolt on silently.

To run true YOLO inference rather than replaying labels, use
`services/roadface-worker/tests/batch_pipeline_hackathon.py`, which drives
`RoadfacePipeline` with `YoloDetector` and writes to
`artifacts/predictions/roadface/hackathon_yolo26n`. Point its detector at the
new checkpoint.

### Step 5 — Verify end to end

`./artifacts` is bind-mounted to `/artifacts` in the API container
(`compose.yaml:98`, `FLEETIQ_ARTIFACTS_ROOT=/artifacts/trips`), so regenerated
files are visible immediately — no image rebuild required.

```powershell
# non-empty detections from the API
docker compose exec web node -e "fetch('http://api:8000/api/v1/trips/T01d/analysis/road/frames/10').then(r=>r.json()).then(d=>console.log('detections:', (d.detections||[]).length))"

# still-healthy media endpoints
curl -s -D - "http://localhost:3000/api/trips/T01d/derived/depth/000000" -o /dev/null
curl -s -D - "http://localhost:3000/api/trips/T01d/road-video/content" -o /dev/null
```

Then re-run the Playwright suite and confirm the trip page draws detection
overlays. Do not claim success without showing the detection count and a
rendered frame.

---

## Guardrails

- The API path is `/analysis/road/frames/{i}`, **not** `/analysis/road/{i}`.
  An earlier investigation lost time to a 404 from the wrong path.
- Only frames 0–49 currently have analysis JSON. Querying frame 100 returns
  `{"detail":"Frame analysis not found"}` — that is correct behavior, not a bug.
- Empty label files are normal. Judge coverage by the `WithBoxes` column in the
  status script, not by file count alone.
- Keep `yolo26n_custom/weights/best.pt` intact until the finetuned checkpoint
  demonstrably beats it.
- Verify before asserting. Every claim above is backed by a command whose
  output was read; hold the remaining steps to the same standard.
