# LocateAnything Dataset Relabeling

The relabel job runs `nvidia/LocateAnything-3B` on every road-facing `image_2` frame and writes KITTI-compatible 2D labels to each trip's `kitti/label2_custom` directory. Original `label_2` files are never modified.

Classes:

- `Motorcycle`
- `Pedestrian`
- `Cyclist`
- `Bus`
- `Car`
- `LongVehicle` for trucks, vans, lorries, trailers, and articulated vehicles

Unknown KITTI 3D fields use sentinel values. They must not be interpreted as predicted dimensions or 3D pose.

## Full Relabel Job

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\relabel_locateanything.py --dataset practice --generation-mode slow --continue-on-error
```

The job is resumable: existing numeric `.txt` labels are skipped unless `--overwrite` is passed. Raw model responses and parsed boxes are appended to `_locateanything_raw.jsonl` in the same output directory.

## Progress

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\check_locateanything_progress.py --dataset practice
```

## Visual Check

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\visualize_kitti_labels.py --dataset practice --trip T06-Sample --label-dir-name label2_custom --start 0 --end 599 --stride 120 --max-frames 5 --mode contact-sheet
```

The full synchronized dashboard can also select the new labels:

```powershell
uv run python scripts\render_trip_dashboard.py --trip T06-Sample --label-dir-name label2_custom --mode window
```

The TTC pipeline can consume them directly:

```powershell
uv run --extra cu130 --extra roadface python scripts\roadface\run_roadface_pipeline.py --dataset practice --trip T06-Sample --detector labels_custom --lane-method plane --depth-source gt --visualize video
```

## Reproducibility and License

The script pins the model revision used during validation. LocateAnything is loaded with `trust_remote_code=True`; the pinned revision avoids silently changing downloaded inference code.

The model card states that the released weights are for research and development under NVIDIA's non-commercial license. Confirm that the hackathon submission and any later deployment comply with that license.
