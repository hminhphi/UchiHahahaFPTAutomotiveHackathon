# Manual Lane Mask Workflow

Use the annotation tool when a curved lane or an occluded marking needs an exact human reference. It creates one pair of files per frame:

- `lane_masks/<frame>.png`: only the left and right painted ego-lane boundaries.
- `road_masks/<frame>.png`: the filled ego-lane floor area between those two boundaries.
- `metadata/<frame>.json`: the editable stroke coordinates and image-size check.

## Annotate a Frame

```powershell
uv run python scripts\roadface\annotate_lane_mask.py --dataset practice --trip T01-Sample --frame 300
```

Controls:

- Left click: add one control point to the selected lane boundary. The tool joins the points using straight segments; add 3 to 6 points to follow a curve.
- `1`: select the left boundary.
- `2`: select the right boundary.
- Right click or `Z`: remove the last control point of the selected boundary.
- `C`: clear the selected boundary.
- `S`: save the frame masks and metadata.
- `[` / `]`: move backward or forward one frame.
- `-` / `+`: reduce or increase stroke thickness.
- `Q` or `Esc`: exit.

For T01 frame 300, trace the inner yellow line as the left ego-lane boundary and the dashed white line as the right ego-lane boundary. Do not trace the outer double-yellow edge, curb, or the lane separator farther to the right.

## Use the Saved Masks

```powershell
uv run python scripts\roadface\demo_plane_lane_offset.py --dataset practice --trip T01-Sample --frame 300 --mask-source files --lane-mask-dir artifacts\roadface\manual_lane_masks\T01-Sample\lane_masks --road-mask-dir artifacts\roadface\manual_lane_masks\T01-Sample\road_masks --output artifacts\roadface\manual_lane_masks\T01-Sample\000300_verified.png
```

The detector reads masks by frame stem, so the same command can be run for every annotated frame. In `files` mode, manually saved masks are authoritative: the visible boundaries and lane floor are kept exactly as annotated, while the road plane is used only for metric fields such as offset.
