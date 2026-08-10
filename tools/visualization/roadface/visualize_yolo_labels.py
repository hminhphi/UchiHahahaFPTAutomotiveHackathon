"""
Visualize YOLO labels to diagnose poor model performance.

This script samples images from the YOLO dataset and renders the bounding boxes
to help identify issues like:
- Very small boxes (<0.1% image area)
- Incorrect class labels
- Box quality issues from LocateAnything
- Class imbalance

Usage:
    python visualize_yolo_labels.py --split train --num-samples 20 --output artifacts/renders/yolo_labels.png
    python visualize_yolo_labels.py --split val --filter-small --output artifacts/renders/yolo_small_boxes.png
    python visualize_yolo_labels.py --split train --class-id 5 --num-samples 10  # Pedestrians only
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

CLASS_NAMES = {
    0: "Car",
    1: "Bus", 
    2: "LongVehicle",
    3: "Motorcycle",
    4: "Cyclist",
    5: "Pedestrian",
}

CLASS_COLORS = {
    0: (59, 178, 246),   # Car - bright blue
    1: (255, 127, 14),   # Bus - orange
    2: (44, 160, 44),    # LongVehicle - green
    3: (214, 39, 40),    # Motorcycle - red
    4: (148, 103, 189),  # Cyclist - purple
    5: (140, 86, 75),    # Pedestrian - brown
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize YOLO dataset labels")
    parser.add_argument("--dataset-root", type=Path, default=Path("artifacts/training/roadface/yolo_dataset_detached"))
    parser.add_argument("--split", choices=("train", "val", "test"), default="train")
    parser.add_argument("--num-samples", type=int, default=20, help="Number of images to sample")
    parser.add_argument("--filter-small", action="store_true", help="Only show images with small boxes (<0.1%% area)")
    parser.add_argument("--filter-large", action="store_true", help="Only show images with large boxes (>10%% area)")
    parser.add_argument("--class-id", type=int, help="Filter to specific class ID (0-5)")
    parser.add_argument("--min-boxes", type=int, help="Minimum number of boxes per image")
    parser.add_argument("--max-boxes", type=int, help="Maximum number of boxes per image")
    parser.add_argument("--output", type=Path, default=Path("artifacts/renders/roadface/yolo_labels_contact_sheet.png"))
    parser.add_argument("--columns", type=int, default=4, help="Columns in contact sheet")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def read_yolo_label(label_path: Path) -> list[dict]:
    """Parse YOLO format label file."""
    if not label_path.exists():
        return []
    
    boxes = []
    for line in label_path.read_text().strip().split("\n"):
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        cls_id = int(parts[0])
        cx, cy, w, h = map(float, parts[1:5])
        boxes.append({
            "class_id": cls_id,
            "cx": cx,
            "cy": cy,
            "w": w,
            "h": h,
            "area": w * h,
        })
    return boxes


def filter_image(boxes: list[dict], args: argparse.Namespace) -> bool:
    """Check if image passes filters."""
    if not boxes:
        return False
    
    if args.class_id is not None:
        if not any(b["class_id"] == args.class_id for b in boxes):
            return False
    
    if args.min_boxes is not None and len(boxes) < args.min_boxes:
        return False
    
    if args.max_boxes is not None and len(boxes) > args.max_boxes:
        return False
    
    if args.filter_small:
        if not any(b["area"] < 0.001 for b in boxes):
            return False
    
    if args.filter_large:
        if not any(b["area"] > 0.1 for b in boxes):
            return False
    
    return True


def render_yolo_boxes(image: np.ndarray, boxes: list[dict], image_name: str) -> np.ndarray:
    """Draw YOLO boxes on image."""
    output = image.copy()
    h, w = image.shape[:2]
    
    # Sort boxes by area (draw large first, small on top)
    boxes = sorted(boxes, key=lambda b: b["area"], reverse=True)
    
    for box in boxes:
        cls_id = box["class_id"]
        cx, cy, bw, bh = box["cx"], box["cy"], box["w"], box["h"]
        
        # Convert normalized YOLO to pixel coords
        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)
        
        color = CLASS_COLORS.get(cls_id, (200, 200, 200))
        
        # Draw box
        thickness = 1 if box["area"] < 0.001 else 2
        cv2.rectangle(output, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)
        
        # Draw label
        cls_name = CLASS_NAMES.get(cls_id, f"Cls{cls_id}")
        area_pct = box["area"] * 100
        label = f"{cls_name} {area_pct:.2f}%"
        
        # Background for text
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(output, (x1, max(0, y1 - th - 4)), (x1 + tw + 4, y1), color, -1)
        cv2.putText(output, label, (x1 + 2, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Footer with stats
    small_count = sum(1 for b in boxes if b["area"] < 0.001)
    footer_text = f"{image_name} | boxes={len(boxes)} | small={small_count}"
    
    cv2.rectangle(output, (0, h - 24), (w, h), (20, 25, 30), -1)
    cv2.putText(output, footer_text, (8, h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 240, 240), 1, cv2.LINE_AA)
    
    return output


def create_contact_sheet(frames: list[np.ndarray], columns: int = 4) -> np.ndarray:
    """Create a contact sheet from multiple frames."""
    if not frames:
        raise ValueError("No frames to render")
    
    target_w = 480
    target_h = 270
    
    tiles = [cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA) for frame in frames]
    rows = (len(tiles) + columns - 1) // columns
    
    # Pad with blank tiles
    blank = np.full((target_h, target_w, 3), 20, dtype=np.uint8)
    tiles.extend([blank] * (rows * columns - len(tiles)))
    
    # Stack into grid
    row_images = []
    for row_idx in range(rows):
        row_tiles = tiles[row_idx * columns : (row_idx + 1) * columns]
        row_images.append(np.hstack(row_tiles))
    
    return np.vstack(row_images)


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    
    dataset_root = args.dataset_root.resolve()
    image_dir = dataset_root / "images" / args.split
    label_dir = dataset_root / "labels" / args.split
    
    if not image_dir.exists():
        raise SystemExit(f"Image directory not found: {image_dir}")
    
    # Get all images
    image_files = sorted(image_dir.glob("*.jpg")) + sorted(image_dir.glob("*.png"))
    print(f"Found {len(image_files)} images in {args.split} split")
    
    # Filter and sample
    candidates = []
    for img_path in image_files:
        label_path = label_dir / f"{img_path.stem}.txt"
        boxes = read_yolo_label(label_path)
        
        if filter_image(boxes, args):
            candidates.append((img_path, boxes))
    
    print(f"After filtering: {len(candidates)} candidates")
    
    if len(candidates) == 0:
        raise SystemExit("No images passed filters")
    
    # Sample
    num_samples = min(args.num_samples, len(candidates))
    sampled = random.sample(candidates, num_samples)
    
    # Render
    rendered_frames = []
    for img_path, boxes in sampled:
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"Warning: Failed to read {img_path}")
            continue
        
        frame = render_yolo_boxes(image, boxes, img_path.stem)
        rendered_frames.append(frame)
    
    if not rendered_frames:
        raise SystemExit("No frames rendered successfully")
    
    # Create contact sheet
    contact = create_contact_sheet(rendered_frames, columns=args.columns)
    
    # Save
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), contact)
    
    print(f"Saved contact sheet: {output_path}")
    print(f"Rendered {len(rendered_frames)} frames in {args.columns} columns")


if __name__ == "__main__":
    main()
