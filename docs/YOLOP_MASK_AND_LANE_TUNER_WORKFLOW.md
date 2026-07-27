# YOLOP Mask and Lane Tuner Workflow

This document separates the two stages of the road-facing lane pipeline:

1. `run_yolop_panoptic_labels.py` runs the YOLOP model and creates AI outputs.
2. `visualize_yolop_lane_offset.py` reads those outputs, connects lane fragments,
   estimates lane offset, and visualizes the result.

Changing sliders in the tuner does not create or modify YOLOP masks. The sliders
only change stage 2.

## Why only five frames currently have masks

`T01-Sample` contains 600 road-camera images. Five evenly spaced frames were
processed during lane-tracker validation:

- `000000`
- `000150`
- `000300`
- `000449`
- `000599`

Current T01 state at the time this guide was written:

- `image_2`: 600 images
- `label2_yolop`: 600 object-label files
- `lane_masks`: 5 masks
- `road_masks`: 5 masks
- `overlays`: 5 images
- `metadata`: 5 files

The updated YOLOP script resumes based on all requested outputs, not only
`label2_yolop`. Therefore it can detect the 595 missing masks even though all 600
label files already exist.

## Output locations

For `T01-Sample`, YOLOP writes:

```text
data/Practice_Dataset/Practice_Dataset/T01-Sample/kitti/label2_yolop/
artifacts/roadface/yolop_panoptic/T01-Sample/lane_masks/
artifacts/roadface/yolop_panoptic/T01-Sample/road_masks/
artifacts/roadface/yolop_panoptic/T01-Sample/overlays/
artifacts/roadface/yolop_panoptic/T01-Sample/metadata/
```

## Step 1: Check the environment

Run from the project root:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\check_roadface_env.py
```

Confirm:

- `torch cuda build` is not `None`.
- `cuda available` is `True`.
- At least one CUDA device is shown.

If CUDA is unavailable, YOLOP can run on CPU but processing the full trip will
be much slower.

## Step 2: Count existing masks

```powershell
$maskRoot = "artifacts\roadface\yolop_panoptic\T01-Sample"

(Get-ChildItem "$maskRoot\lane_masks" -Filter *.png).Count
(Get-ChildItem "$maskRoot\road_masks" -Filter *.png).Count
```

The expected final count for T01 is `600` for each folder.

## Step 3: Resume and generate only missing masks

Recommended command:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\run_yolop_panoptic_labels.py `
  --dataset practice `
  --trip T01-Sample `
  --device cuda:0 `
  --no-save-overlays
```

Important behavior:

- Existing complete frames are skipped.
- Frames with labels but missing masks are processed.
- Existing labels are preserved.
- `--no-save-overlays` saves disk space and does not affect the lane tuner.
- Progress is printed after the first processed frame and every 50 frames.

Remove `--no-save-overlays` if annotated YOLOP preview images are also required.

## Step 4: Force regeneration of every T01 output

Use this only when the model settings changed or existing masks are suspected to
be incorrect:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\run_yolop_panoptic_labels.py `
  --dataset practice `
  --trip T01-Sample `
  --device cuda:0 `
  --overwrite `
  --no-save-overlays
```

`--overwrite` reruns inference for all selected frames and rewrites masks,
metadata, and labels.

## Step 5: Process a bounded range first

The following command processes frames 0 through 199:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\run_yolop_panoptic_labels.py `
  --dataset practice `
  --trip T01-Sample `
  --start 0 `
  --end 199 `
  --device cuda:0 `
  --no-save-overlays
```

Useful variants:

```powershell
# One frame.
uv run --extra cu130 --extra roadface python scripts\roadface\run_yolop_panoptic_labels.py `
  --dataset practice --trip T01-Sample --frame 300 --overwrite

# Every fifth frame in a range.
uv run --extra cu130 --extra roadface python scripts\roadface\run_yolop_panoptic_labels.py `
  --dataset practice --trip T01-Sample --start 0 --end 599 --stride 5

# First 50 selected frames.
uv run --extra cu130 --extra roadface python scripts\roadface\run_yolop_panoptic_labels.py `
  --dataset practice --trip T01-Sample --max-frames 50
```

## Step 6: Verify completion

```powershell
$imageRoot = "data\Practice_Dataset\Practice_Dataset\T01-Sample\kitti\image_2"
$maskRoot = "artifacts\roadface\yolop_panoptic\T01-Sample"

"images:     $((Get-ChildItem $imageRoot -File).Count)"
"lane masks: $((Get-ChildItem "$maskRoot\lane_masks" -Filter *.png).Count)"
"road masks: $((Get-ChildItem "$maskRoot\road_masks" -Filter *.png).Count)"
"metadata:   $((Get-ChildItem "$maskRoot\metadata" -Filter *.json).Count)"
```

For a complete T01 run, all four values should be `600`.

## Step 7: Inspect YOLOP outputs

Open the combined road-mask, lane-mask, and vehicle view while running:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\run_yolop_panoptic_labels.py `
  --dataset practice `
  --trip T01-Sample `
  --start 0 `
  --end 99 `
  --visualize window `
  --fps 20
```

Press `Q` or `Esc` to stop.

## Step 8: Start the lane-offset tuner

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\visualize_yolop_lane_offset.py `
  --dataset practice `
  --trip T01-Sample `
  --mode tuner
```

The tuner automatically lists only frames with available lane masks. After all
T01 masks are generated, its frame count should change from `5` to `600`.

Tuner controls:

- `Play/Pause`: start or stop playback.
- `Prev/Next`: move one available frame.
- `birdseye`: cycle through `birdseye`, `vector`, and `scanline`.
- `Reset`: restore command-line/default values.
- `Save`: save the current rendered frame.
- `FPS +/-`: change playback speed.
- `Win +/-`: change the number of sliding windows.
- Bottom timeline: click or drag to select a frame.

Keyboard controls:

- `Space`: play or pause.
- `A` / `D`: previous or next frame.
- `S`: save.
- `R`: reset.
- `Q` / `Esc`: quit.

## Tuner slider meanings

| Control | Effect | Increase when | Decrease when |
|---|---|---|---|
| Mask ROI top | Removes mask pixels above this image height | Sky/buildings enter the fit | Useful far-lane pixels are cut |
| IPM top Y | Moves the top of the ground-plane trapezoid downward | Far region is unstable | Curves are cut too early |
| IPM top half-width | Widens the trapezoid near the horizon | Curved lane leaves the IPM area | Adjacent lanes enter the fit |
| IPM bottom margin | Narrows the trapezoid at the image bottom | Curb/sidewalk enters the fit | Ego-lane boundary is cut |
| Bird destination margin | Changes nominal bird's-eye lane width | Fitted lane is too wide | Fitted lane is too narrow |
| Window search margin | Allows windows to reconnect farther fragments | Mask is broken or sharply curved | Windows jump to adjacent markings |
| Minimum lane pixels | Requires stronger pixel support | Noise is accepted as a lane | Dashed or occluded lane is rejected |
| Lane width tolerance | Allows more lane-width variation | Perspective calibration is imperfect | Adjacent-lane pairs are accepted |
| Temporal new-frame weight | Gives more weight to the current frame | Tracker reacts too slowly | Result flickers between frames |

## Preset from the supplied tuner screenshot

The screenshot corresponds to:

```text
FPS                         20
Sliding windows              5
Mask ROI top               55%
IPM top Y                  62%
IPM top half-width          8%
IPM bottom margin          16%
Bird destination margin    21%
Window search margin       10%
Minimum lane pixels        63
Lane width tolerance       28%
Temporal new-frame weight  41%
```

Equivalent command-line options:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\visualize_yolop_lane_offset.py `
  --dataset practice `
  --trip T01-Sample `
  --mode tuner `
  --fps 20 `
  --sliding-windows 5 `
  --roi-top-ratio 0.55 `
  --perspective-top-y-ratio 0.62 `
  --perspective-top-half-width-ratio 0.08 `
  --perspective-bottom-margin-ratio 0.16 `
  --bird-destination-margin-ratio 0.21 `
  --window-margin-ratio 0.10 `
  --min-lane-pixels 63 `
  --bird-width-tolerance 0.28 `
  --temporal-alpha 0.41
```

## Export a lane-offset video with the tuned values

Change only `--mode tuner` to `--mode video`:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\visualize_yolop_lane_offset.py `
  --dataset practice `
  --trip T01-Sample `
  --mode video `
  --fps 20 `
  --sliding-windows 5 `
  --roi-top-ratio 0.55 `
  --perspective-top-y-ratio 0.62 `
  --perspective-top-half-width-ratio 0.08 `
  --perspective-bottom-margin-ratio 0.16 `
  --bird-destination-margin-ratio 0.21 `
  --window-margin-ratio 0.10 `
  --min-lane-pixels 63 `
  --bird-width-tolerance 0.28 `
  --temporal-alpha 0.41
```

Output:

```text
artifacts/roadface/yolop_lane_offset/T01-Sample_lane_offset_video.mp4
```

## YOLOP generation options

| Option | Default | Description |
|---|---:|---|
| `--dataset` | `practice` | Select `practice`, `redacted`, or `all` |
| `--dataset-root` | none | Override the dataset root |
| `--trip` | all trips | Select one trip; may be repeated |
| `--frame` | none | Process exactly one frame |
| `--start` | `0` | First frame in a range |
| `--end` | last | Last frame in a range |
| `--stride` | `1` | Process every Nth frame |
| `--max-frames` | unlimited | Limit the number of selected frames |
| `--device` | `auto` | Use `cuda:0`, `cuda`, or `cpu` explicitly |
| `--imgsz` | `640` | YOLOP inference input size |
| `--conf` | `0.25` | Object-detection confidence threshold |
| `--iou` | `0.45` | NMS IoU threshold |
| `--max-det` | `80` | Maximum objects per frame |
| `--overwrite` | false | Regenerate every selected output |
| `--save-masks` | true | Save road and lane masks |
| `--no-save-masks` | false | Disable road/lane mask output |
| `--save-overlays` | true | Save annotated preview images |
| `--no-save-overlays` | false | Disable preview images to save disk |
| `--visualize` | `none` | Select `none`, `window`, `video`, or `gif` |
| `--fps` | `20` | Playback/export frame rate |
| `--label-dir-name` | `label2_yolop` | KITTI object-label output folder |
| `--output-dir` | `artifacts/roadface/yolop_panoptic` | Mask/metadata output root |
| `--manifest-only` | false | List selected trips and frames without inference |

## Common problems

### Tuner shows fewer frames than the trip contains

The missing frames do not have `lane_masks`. Run the resume command in Step 3.

### The resume command skips everything

Use the updated `run_yolop_panoptic_labels.py`. Its resume check includes masks
and metadata. Use `--overwrite` only if all selected frames must be regenerated.

### CUDA out of memory

Close other GPU processes and retry with:

```powershell
--device cuda:0 --imgsz 512 --no-save-overlays
```

Reducing `--imgsz` can change mask quality, so compare several frames before
processing the full trip.

### PowerShell multiline command fails

The backtick must be the final character on the line. Do not place spaces after
it.
