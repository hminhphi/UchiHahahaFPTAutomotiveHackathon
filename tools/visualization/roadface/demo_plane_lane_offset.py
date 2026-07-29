from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from fleetiq_training_roadface.experimental import (
    compute_road_and_lane,
    detections_from_labels,
    detections_ignore_mask,
    draw_overlay,
    estimate_plane_lane,
    find_image,
    load_gt_depth,
    parse_calibration,
    read_image,
    resolve_trip,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plane-based lane offset demo: AI/external masks -> road plane -> metric lane corridor."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--trip", default="T06-Sample")
    parser.add_argument("--frame", type=int, default=100)
    parser.add_argument(
        "--mask-source",
        choices=("classical", "transformers", "files"),
        default="classical",
        help="classical is only a fallback; transformers/files are the intended AI-mask paths.",
    )
    parser.add_argument(
        "--seg-model",
        default="nvidia/segformer-b0-finetuned-cityscapes-1024-1024",
        help="Hugging Face semantic/image segmentation model used when --mask-source transformers.",
    )
    parser.add_argument("--road-mask-dir", type=Path, help="Directory with frame-stem road masks for --mask-source files.")
    parser.add_argument("--lane-mask-dir", type=Path, help="Directory with frame-stem lane masks for --mask-source files.")
    parser.add_argument("--depth-policy", choices=("previous", "nearest"), default="nearest")
    parser.add_argument("--lane-width-m", type=float, default=3.7)
    parser.add_argument("--lookahead-m", type=float, default=10.0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


class TransformersSegmenter:
    def __init__(self, model_id: str) -> None:
        try:
            import torch
            from PIL import Image
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Install roadface AI deps first: "
                "uv sync --all-packages --extra cu130 --extra models"
            ) from exc
        device = 0 if torch.cuda.is_available() else -1
        self.pipe = pipeline("image-segmentation", model=model_id, device=device)
        self.image_cls = Image

    def __call__(self, image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        outputs = self.pipe(self.image_cls.fromarray(rgb))
        h, w = image_bgr.shape[:2]
        road = np.zeros((h, w), dtype=np.uint8)
        lane = np.zeros((h, w), dtype=np.uint8)
        for item in outputs:
            label = str(item.get("label", "")).lower()
            raw_mask = np.asarray(item.get("mask"), dtype=np.uint8)
            if raw_mask.ndim == 3:
                raw_mask = raw_mask[:, :, 0]
            raw_mask = cv2.resize(raw_mask, (w, h), interpolation=cv2.INTER_NEAREST)
            binary = np.where(raw_mask > 0, 255, 0).astype(np.uint8)
            if any(token in label for token in ("road", "drivable", "route")):
                road = cv2.bitwise_or(road, binary)
            if any(token in label for token in ("lane", "lane marking", "road line")):
                lane = cv2.bitwise_or(lane, binary)
        return road, lane


def load_binary_mask(mask_dir: Path | None, stem: str, shape: tuple[int, int]) -> np.ndarray | None:
    if mask_dir is None:
        return None
    path = find_image(mask_dir, stem)
    if path is None:
        return None
    mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return None
    mask = cv2.resize(mask, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return np.where(mask > 0, 255, 0).astype(np.uint8)


def masks_from_source(args: argparse.Namespace, image: np.ndarray, stem: str) -> tuple[np.ndarray | None, np.ndarray | None, str]:
    if args.mask_source == "files":
        return (
            load_binary_mask(args.road_mask_dir, stem, image.shape[:2]),
            load_binary_mask(args.lane_mask_dir, stem, image.shape[:2]),
            "external mask files",
        )
    if args.mask_source == "transformers":
        segmenter = TransformersSegmenter(args.seg_model)
        road, lane = segmenter(image)
        return road, lane, f"AI segmentation: {args.seg_model}"
    road, _, _, _ = compute_road_and_lane(image)
    return road, None, "classical road fallback only"


def draw_status_panel(image: np.ndarray, lines: list[str]) -> np.ndarray:
    out = image.copy()
    panel_h = 120
    panel = np.full((panel_h, out.shape[1], 3), (28, 38, 48), dtype=np.uint8)
    for idx, line in enumerate(lines):
        cv2.putText(
            panel,
            line,
            (16, 28 + idx * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (235, 242, 248),
            1,
            cv2.LINE_AA,
        )
    return np.vstack([out, panel])


def main() -> None:
    args = parse_args()
    trip_dir = resolve_trip(args.trip, args.dataset)
    stem = f"{args.frame:06d}"
    image = read_image(find_image(trip_dir / "kitti" / "image_2", stem))
    if image is None:
        raise FileNotFoundError(f"Missing frame {stem} in {trip_dir / 'kitti' / 'image_2'}")
    calibration = parse_calibration(trip_dir / "kitti" / "calib" / f"{stem}.txt")
    depth = load_gt_depth(trip_dir, args.frame, args.depth_policy)
    road_mask, lane_mask, mask_note = masks_from_source(args, image, stem)
    detections = detections_from_labels(trip_dir / "kitti" / "label_2" / f"{stem}.txt", calibration, image.shape)
    ignore_mask = detections_ignore_mask(image.shape, detections) if detections else None
    estimate = estimate_plane_lane(
        image,
        depth,
        calibration,
        road_mask=road_mask,
        lane_mask=lane_mask,
        ignore_mask=ignore_mask,
        lane_width_m=args.lane_width_m,
        lookahead_m=args.lookahead_m,
        trusted_external_masks=args.mask_source == "files",
    )
    overlay = draw_overlay(
        image,
        [],
        estimate.road_mask,
        estimate.lane_mask,
        estimate.lane_offset_m,
        corridor_mask=estimate.corridor_mask,
        vertical_corridor_mask=estimate.vertical_corridor_mask,
    )
    lines = [
        f"{trip_dir.name} frame {stem} | plane-based lane offset",
        f"mask={mask_note} | plane={estimate.plane.source} inliers={estimate.plane.inlier_count} ratio={estimate.plane.inlier_ratio:.2f}",
        f"offset@{args.lookahead_m:.0f}m={estimate.lane_offset_m:+.2f}m heading={estimate.heading_deg:+.2f}deg conf={estimate.confidence:.2f}",
        f"note={estimate.note}",
    ]
    rendered = draw_status_panel(overlay, lines)
    output = args.output or Path("artifacts/roadface/lane_demo") / f"{trip_dir.name}_{stem}_plane_lane.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), rendered)
    print(f"Wrote {output.resolve()}")


if __name__ == "__main__":
    main()
