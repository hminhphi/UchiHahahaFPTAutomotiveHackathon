from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.roadface.roadface_lib import discover_trips


MODEL_ID = "nvidia/LocateAnything-3B"
MODEL_REVISION = "c32291ca5e996f5a7a485845b4f57a233936bba0"
OUTPUT_DIR_NAME = "label2_custom"

# Put the more specific vehicle categories before Car. Cross-class duplicate
# removal keeps this priority when the model returns both "car" and "truck".
PROMPT_CATEGORIES = [
    "bus",
    "long vehicle such as truck, van, lorry, trailer, or articulated vehicle",
    "car",
    "motorcycle",
    "bicycle or bicyclist",
    "person or pedestrian",
]

REF_OR_BOX_PATTERN = re.compile(
    r"<ref>(?P<label>.*?)</ref>"
    r"|<box>\s*<(?P<x1>\d+)>\s*<(?P<y1>\d+)>\s*<(?P<x2>\d+)>\s*<(?P<y2>\d+)>\s*</box>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class LocatedBox:
    object_type: str
    bbox: tuple[float, float, float, float]
    raw_label: str


def canonical_object_type(raw_label: str) -> str | None:
    label = re.sub(r"\s+", " ", raw_label.strip().lower())
    if any(token in label for token in ("bus", "coach")):
        return "Bus"
    if any(token in label for token in ("truck", "van", "lorry", "trailer", "articulated", "long vehicle")):
        return "LongVehicle"
    if any(token in label for token in ("motorcycle", "motorbike", "motor bike", "scooter")):
        return "Motorcycle"
    if any(token in label for token in ("bicycle", "bicyclist", "cyclist", "bike rider")):
        return "Cyclist"
    if any(token in label for token in ("person", "pedestrian", "people", "human")):
        return "Pedestrian"
    if any(token in label for token in ("car", "automobile", "sedan", "suv", "hatchback")):
        return "Car"
    return None


def valid_box(
    bbox: Iterable[float],
    width: int,
    height: int,
    min_size_px: float = 3.0,
) -> tuple[float, float, float, float] | None:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    x1 = min(max(x1, 0.0), width - 1.0)
    x2 = min(max(x2, 0.0), width - 1.0)
    y1 = min(max(y1, 0.0), height - 1.0)
    y2 = min(max(y2, 0.0), height - 1.0)
    if x2 - x1 < min_size_px or y2 - y1 < min_size_px:
        return None
    return x1, y1, x2, y2


def parse_locateanything_answer(
    answer: str,
    width: int,
    height: int,
    min_size_px: float = 3.0,
) -> list[LocatedBox]:
    current_label = ""
    boxes: list[LocatedBox] = []
    for match in REF_OR_BOX_PATTERN.finditer(answer):
        label = match.group("label")
        if label is not None:
            current_label = label
            continue
        object_type = canonical_object_type(current_label)
        if object_type is None:
            continue
        quantized = [int(match.group(name)) for name in ("x1", "y1", "x2", "y2")]
        bbox = valid_box(
            (
                quantized[0] / 1000.0 * width,
                quantized[1] / 1000.0 * height,
                quantized[2] / 1000.0 * width,
                quantized[3] / 1000.0 * height,
            ),
            width,
            height,
            min_size_px,
        )
        if bbox is not None:
            boxes.append(LocatedBox(object_type, bbox, current_label.strip()))
    return deduplicate_boxes(truncate_runaway_box_chain(boxes))


def truncate_runaway_box_chain(
    boxes: list[LocatedBox],
    minimum_chain: int = 4,
    tolerance_px: float = 1.6,
) -> list[LocatedBox]:
    """Drop a malformed decoding tail made of adjacent, equal-height boxes."""
    chain_start = 0
    chain_length = 1
    for index in range(1, len(boxes)):
        previous = boxes[index - 1]
        current = boxes[index]
        py1, py2 = previous.bbox[1], previous.bbox[3]
        cy1, cy2 = current.bbox[1], current.bbox[3]
        chained = (
            current.object_type == previous.object_type
            and abs(cy1 - py1) <= tolerance_px
            and abs(cy2 - py2) <= tolerance_px
            and abs(current.bbox[0] - previous.bbox[2]) <= tolerance_px
        )
        if chained:
            if chain_length == 1:
                chain_start = index - 1
            chain_length += 1
            if chain_length >= minimum_chain:
                return boxes[:chain_start]
        else:
            chain_start = index
            chain_length = 1
    return boxes


def bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return intersection / max(area_a + area_b - intersection, 1e-6)


def deduplicate_boxes(boxes: list[LocatedBox], iou_threshold: float = 0.82) -> list[LocatedBox]:
    priority = {
        "Bus": 0,
        "LongVehicle": 1,
        "Car": 2,
        "Motorcycle": 3,
        "Cyclist": 4,
        "Pedestrian": 5,
    }
    vehicle_types = {"Bus", "LongVehicle", "Car"}
    ordered = sorted(
        enumerate(boxes),
        key=lambda item: (priority.get(item[1].object_type, 99), item[0]),
    )
    kept: list[LocatedBox] = []
    for _, candidate in ordered:
        duplicate = False
        for existing in kept:
            same_type = candidate.object_type == existing.object_type
            same_vehicle = candidate.object_type in vehicle_types and existing.object_type in vehicle_types
            if (same_type or same_vehicle) and bbox_iou(candidate.bbox, existing.bbox) >= iou_threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def kitti_2d_line(box: LocatedBox) -> str:
    x1, y1, x2, y2 = box.bbox
    # Unknown 3D fields use KITTI sentinel values. This keeps the original 2D
    # box exact and prevents consumers from treating invented 3D pose as truth.
    return (
        f"{box.object_type} 0.00 0 -10.00 "
        f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f} "
        "-1.00 -1.00 -1.00 -1000.00 -1000.00 -1000.00 -10.00"
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def answer_as_text(response: Any, tokenizer: Any) -> str:
    answer = response[0] if isinstance(response, tuple) else response
    if isinstance(answer, str):
        return answer
    if isinstance(answer, list) and answer and isinstance(answer[0], str):
        return answer[0]
    if hasattr(answer, "detach"):
        tokens = answer.detach().cpu()
        if getattr(tokens, "ndim", 1) > 1:
            tokens = tokens[0]
        return tokenizer.decode(tokens, skip_special_tokens=False)
    return str(answer)


class LocateAnythingWorker:
    def __init__(self, model_id: str, revision: str, device: str) -> None:
        try:
            import torch
            from transformers import AutoModel, AutoProcessor, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "LocateAnything dependencies are missing. Run: "
                "uv sync --extra cu130 --extra roadface"
            ) from exc

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is unavailable. Refusing to run a 3B relabel job on CPU; "
                "fix the CUDA torch environment or pass --device cpu explicitly."
            )
        self.torch = torch
        self.device = device
        self.dtype = torch.bfloat16 if device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=True,
        )
        self.processor = AutoProcessor.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=True,
        )
        self.model = AutoModel.from_pretrained(
            model_id,
            revision=revision,
            torch_dtype=self.dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        ).to(device).eval()
        if device == "cuda":
            torch.backends.cuda.matmul.allow_tf32 = True

    def detect(
        self,
        image: Any,
        generation_mode: str,
        max_new_tokens: int,
    ) -> str:
        categories = "</c>".join(PROMPT_CATEGORIES)
        prompt = f"Locate all the instances that matches the following description: {categories}."
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = self.processor.py_apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        images, videos = self.processor.process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=images,
            videos=videos,
            return_tensors="pt",
        ).to(self.device)
        pixel_values = inputs["pixel_values"].to(self.dtype)
        with self.torch.inference_mode():
            response = self.model.generate(
                pixel_values=pixel_values,
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                image_grid_hws=inputs.get("image_grid_hws"),
                tokenizer=self.tokenizer,
                max_new_tokens=max_new_tokens,
                use_cache=True,
                generation_mode=generation_mode,
                temperature=0.0,
                do_sample=False,
                verbose=False,
            )
        return answer_as_text(response, self.tokenizer)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Relabel all road-facing image_2 frames with NVIDIA LocateAnything-3B."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--trip", action="append", help="Repeat to select trips; omit for all.")
    parser.add_argument("--model", default=MODEL_ID)
    parser.add_argument("--revision", default=MODEL_REVISION)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--generation-mode", choices=("fast", "hybrid", "slow"), default="slow")
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--min-box-size", type=float, default=3.0)
    parser.add_argument("--output-dir-name", default=OUTPUT_DIR_NAME)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="List selected trips/frame counts without loading the model.",
    )
    return parser.parse_args()


def selected_trips(args: argparse.Namespace) -> list[Path]:
    source = str(args.dataset_root) if args.dataset_root is not None else args.dataset
    trips = discover_trips(source)
    requested = set(args.trip or [])
    selected = [trip for trip in trips if not requested or trip.name in requested]
    if not selected:
        raise SystemExit("No matching trips found.")
    return selected


def selected_images(trip_dir: Path, args: argparse.Namespace) -> list[Path]:
    images = [
        path
        for path in sorted((trip_dir / "kitti" / "image_2").iterdir())
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stem.isdigit()
    ]
    return [
        path
        for path in images
        if int(path.stem) >= args.start
        and (args.end is None or int(path.stem) <= args.end)
        and (int(path.stem) - args.start) % max(1, args.stride) == 0
    ]


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def run_trip(
    worker: LocateAnythingWorker,
    trip_dir: Path,
    args: argparse.Namespace,
    remaining: int | None,
) -> tuple[int, int, int]:
    from PIL import Image

    output_dir = trip_dir / "kitti" / args.output_dir_name
    raw_path = output_dir / "_locateanything_raw.jsonl"
    images = selected_images(trip_dir, args)
    processed = 0
    skipped = 0
    errors = 0
    for image_path in images:
        if remaining is not None and processed >= remaining:
            break
        label_path = output_dir / f"{image_path.stem}.txt"
        if label_path.exists() and not args.overwrite:
            skipped += 1
            continue
        started = time.perf_counter()
        try:
            image = Image.open(image_path).convert("RGB")
            answer = worker.detect(image, args.generation_mode, args.max_new_tokens)
            boxes = parse_locateanything_answer(
                answer,
                image.width,
                image.height,
                args.min_box_size,
            )
            label_text = "\n".join(kitti_2d_line(box) for box in boxes)
            if label_text:
                label_text += "\n"
            atomic_write_text(label_path, label_text)
            append_jsonl(
                raw_path,
                {
                    "trip": trip_dir.name,
                    "frame": int(image_path.stem),
                    "image": str(image_path),
                    "model": args.model,
                    "revision": args.revision,
                    "generation_mode": args.generation_mode,
                    "categories": PROMPT_CATEGORIES,
                    "elapsed_s": round(time.perf_counter() - started, 4),
                    "boxes": [asdict(box) for box in boxes],
                    "answer": answer,
                },
            )
            processed += 1
            if processed == 1 or processed % 25 == 0:
                print(
                    f"{trip_dir.name}: labeled={processed} skipped={skipped} "
                    f"frame={image_path.stem} boxes={len(boxes)}"
                )
        except Exception as exc:
            errors += 1
            append_jsonl(
                raw_path,
                {
                    "trip": trip_dir.name,
                    "frame": int(image_path.stem),
                    "image": str(image_path),
                    "model": args.model,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            if not args.continue_on_error:
                raise
            print(f"{trip_dir.name} frame {image_path.stem}: {type(exc).__name__}: {exc}")
    return processed, skipped, errors


def main() -> None:
    args = parse_args()
    trips = selected_trips(args)
    counts = [(trip, len(selected_images(trip, args))) for trip in trips]
    total = sum(count for _, count in counts)
    print(f"Selected {len(trips)} trips, {total} image_2 frames")
    for trip, count in counts:
        print(f"  {trip.name}: {count}")
    if args.manifest_only:
        return

    worker = LocateAnythingWorker(args.model, args.revision, args.device)
    total_processed = 0
    total_skipped = 0
    total_errors = 0
    for trip, _ in counts:
        remaining = None if args.max_frames is None else max(0, args.max_frames - total_processed)
        if remaining == 0:
            break
        processed, skipped, errors = run_trip(worker, trip, args, remaining)
        total_processed += processed
        total_skipped += skipped
        total_errors += errors
    print(
        f"Finished: labeled={total_processed} skipped={total_skipped} "
        f"errors={total_errors} output=kitti/{args.output_dir_name}"
    )


if __name__ == "__main__":
    main()
