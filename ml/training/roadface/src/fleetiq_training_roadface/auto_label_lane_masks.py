from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

try:
    import cv2
    import numpy as np
except ModuleNotFoundError as exc:
    cv2 = None
    np = None
    RUNTIME_IMPORT_ERROR: ModuleNotFoundError | None = exc
else:
    RUNTIME_IMPORT_ERROR = None


EXECUTABLE_MODELS = {
    "yolop": {
        "description": "YOLOP: traffic objects + drivable area + lane-line segmentation, pretrained on BDD100K.",
        "source": "HF card/space references Riser/YOLOP and pytorch/YOLOP; executable weights are loaded via torch.hub hustvl/yolop.",
    },
    "segformer-cityscapes": {
        "description": "NVIDIA SegFormer Cityscapes semantic segmentation. Good road mask prior, no lane-marking class.",
        "repo_id": "nvidia/segformer-b0-finetuned-cityscapes-1024-1024",
    },
    "keras-road-lane": {
        "description": "Keras U-Net ResNet50 road/lane semantic segmentation. Optional; requires Keras/TensorFlow runtime.",
        "repo_id": "yaraa11/road-lane-semantic-segmentation-unet-resnet50",
    },
}

DOWNLOAD_ONLY_MODELS = {
    "ufld-carla": {
        "description": "CARLA UFLD weights. Downloaded only because the HF repo does not expose a self-contained Python decoder.",
        "repo_id": "jkdxbns/autonomous-driving-carla",
    },
    "bdd100k-unet-ncnn": {
        "description": "BDD100K binary lane segmentation UNet/NCNN package. Downloaded only unless its upstream repo decoder is added.",
        "repo_id": "nickpai/lane-detection-unet-ncnn",
    },
    "ufld-litert": {
        "description": "Ultra-Fast-Lane-Detection LiteRT package. Downloaded only; Python LiteRT runtime is not part of this repo.",
        "repo_id": "litert-community/Ultra-Fast-Lane-Detection-LiteRT",
    },
}


@dataclass
class LaneMaskResult:
    road_mask: np.ndarray | None
    lane_mask: np.ndarray | None
    confidence: float
    metadata: dict[str, object]


class LaneMaskModel(Protocol):
    model_key: str

    def predict(self, image_bgr: np.ndarray) -> LaneMaskResult:
        ...


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and run pretrained road-view lane/road segmentation models on KITTI image_2 frames."
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument(
        "--trip",
        default="T01-Sample",
        help="Trip name, or 'all' to process all trips in --dataset.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["yolop", "segformer-cityscapes"],
        help="Model keys. Use --list-models to inspect supported keys.",
    )
    parser.add_argument("--frame", type=int, help="Single frame id, e.g. 300.")
    parser.add_argument("--frames", type=int, nargs="+", help="Explicit list of frame ids.")
    parser.add_argument(
        "--sample-count",
        type=int,
        default=5,
        help="If --frame/--frames are omitted, sample this many evenly spaced frames per trip.",
    )
    parser.add_argument(
        "--all-frames",
        action="store_true",
        help="Process every image_2 frame. This can be slow and will produce many files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/training/roadface/ai_lane_masks"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/models/cache"),
        help="Local cache for Hugging Face and torch.hub downloads.",
    )
    parser.add_argument("--conf-threshold", type=float, default=0.45)
    parser.add_argument("--lane-dilate-px", type=int, default=3)
    parser.add_argument("--road-close-px", type=int, default=9)
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    return parser.parse_args()


def print_model_registry() -> None:
    print("Executable models:")
    for key, info in EXECUTABLE_MODELS.items():
        repo = f" ({info['repo_id']})" if "repo_id" in info else ""
        print(f"  {key}{repo}: {info['description']}")
    print("Download-only models:")
    for key, info in DOWNLOAD_ONLY_MODELS.items():
        print(f"  {key} ({info['repo_id']}): {info['description']}")


def normalize_mask(mask: np.ndarray | None, shape_hw: tuple[int, int], close_px: int = 0, dilate_px: int = 0) -> np.ndarray | None:
    if mask is None:
        return None
    h, w = shape_hw
    if mask.shape[:2] != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    mask = np.where(mask > 0, 255, 0).astype(np.uint8)
    if close_px >= 3:
        k = close_px | 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    if dilate_px >= 2:
        k = dilate_px | 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        mask = cv2.dilate(mask, kernel, iterations=1)
    return mask


def overlay_masks(image_bgr: np.ndarray, road_mask: np.ndarray | None, lane_mask: np.ndarray | None, title: str) -> np.ndarray:
    out = image_bgr.copy()
    if road_mask is not None:
        road = np.zeros_like(out)
        road[:, :, 1] = 180
        out = np.where(road_mask[:, :, None] > 0, cv2.addWeighted(out, 0.72, road, 0.28, 0), out)
    if lane_mask is not None:
        lane = np.zeros_like(out)
        lane[:, :, 1] = 230
        lane[:, :, 2] = 255
        out = np.where(lane_mask[:, :, None] > 0, lane, out)
    cv2.rectangle(out, (8, 8), (min(out.shape[1] - 1, 8 + len(title) * 9), 34), (20, 25, 30), -1)
    cv2.putText(out, title, (16, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (245, 245, 245), 1, cv2.LINE_AA)
    return out


class YolopLaneModel:
    model_key = "yolop"

    def __init__(self, cache_dir: Path, threshold: float) -> None:
        os.environ.setdefault("TORCH_HOME", str((cache_dir / "torch").resolve()))
        import torch

        self.torch = torch
        self.threshold = threshold
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.model = torch.hub.load("hustvl/yolop", "yolop", pretrained=True)
        self.model.to(self.device).eval()

    def _foreground_mask(self, tensor: object, out_hw: tuple[int, int]) -> tuple[np.ndarray, float]:
        torch = self.torch
        if isinstance(tensor, (list, tuple)):
            tensor = tensor[0]
        logits = tensor.detach()
        if logits.ndim == 3:
            logits = logits.unsqueeze(0)
        if logits.ndim != 4:
            raise RuntimeError(f"Unsupported YOLOP segmentation output shape: {tuple(logits.shape)}")
        if logits.shape[1] == 1:
            score = torch.sigmoid(logits[:, 0])
        else:
            score = torch.softmax(logits, dim=1)[:, 1]
        score_np = score[0].float().cpu().numpy()
        score_np = cv2.resize(score_np, (out_hw[1], out_hw[0]), interpolation=cv2.INTER_LINEAR)
        return (score_np >= self.threshold).astype(np.uint8) * 255, float(np.nanmean(score_np))

    def predict(self, image_bgr: np.ndarray) -> LaneMaskResult:
        torch = self.torch
        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (640, 640), interpolation=cv2.INTER_LINEAR)
        tensor = torch.from_numpy(resized).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        tensor = tensor.to(self.device)
        with torch.inference_mode():
            outputs = self.model(tensor)
        if not isinstance(outputs, (list, tuple)) or len(outputs) < 3:
            raise RuntimeError("YOLOP did not return det_out, da_seg_out, ll_seg_out.")
        _det_out, da_seg_out, ll_seg_out = outputs[:3]
        road_mask, road_conf = self._foreground_mask(da_seg_out, (h, w))
        lane_mask, lane_conf = self._foreground_mask(ll_seg_out, (h, w))
        return LaneMaskResult(
            road_mask=road_mask,
            lane_mask=lane_mask,
            confidence=float(max(road_conf, lane_conf)),
            metadata={
                "model": self.model_key,
                "device": str(self.device),
                "threshold": self.threshold,
                "road_score_mean": road_conf,
                "lane_score_mean": lane_conf,
            },
        )


class SegFormerCityscapesModel:
    model_key = "segformer-cityscapes"

    def __init__(self, repo_id: str, cache_dir: Path) -> None:
        import torch
        from PIL import Image
        from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation

        self.torch = torch
        self.image_cls = Image
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        hf_cache = cache_dir / "huggingface"
        self.processor = AutoImageProcessor.from_pretrained(repo_id, cache_dir=hf_cache)
        self.model = AutoModelForSemanticSegmentation.from_pretrained(repo_id, cache_dir=hf_cache)
        self.model.to(self.device).eval()
        self.repo_id = repo_id

    def predict(self, image_bgr: np.ndarray) -> LaneMaskResult:
        torch = self.torch
        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_image = self.image_cls.fromarray(rgb)
        inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)
        with torch.inference_mode():
            logits = self.model(**inputs).logits
            logits = torch.nn.functional.interpolate(
                logits,
                size=(h, w),
                mode="bilinear",
                align_corners=False,
            )
            pred = logits.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
        id2label = {int(k): str(v).lower() for k, v in self.model.config.id2label.items()}
        road_ids = [idx for idx, label in id2label.items() if label == "road"]
        lane_ids = [idx for idx, label in id2label.items() if "lane" in label or "marking" in label]
        road_mask = np.isin(pred, road_ids).astype(np.uint8) * 255 if road_ids else None
        lane_mask = np.isin(pred, lane_ids).astype(np.uint8) * 255 if lane_ids else None
        return LaneMaskResult(
            road_mask=road_mask,
            lane_mask=lane_mask,
            confidence=1.0,
            metadata={
                "model": self.model_key,
                "repo_id": self.repo_id,
                "device": str(self.device),
                "road_ids": road_ids,
                "lane_ids": lane_ids,
                "note": "Cityscapes has a road class but generally no lane-marking class.",
            },
        )


class KerasRoadLaneModel:
    model_key = "keras-road-lane"

    def __init__(self, repo_id: str) -> None:
        try:
            import keras
        except ImportError as exc:
            raise RuntimeError("Install Keras/TensorFlow before using --models keras-road-lane.") from exc
        self.keras = keras
        self.repo_id = repo_id
        self.model = keras.saving.load_model(f"hf://{repo_id}", compile=False)

    def predict(self, image_bgr: np.ndarray) -> LaneMaskResult:
        h, w = image_bgr.shape[:2]
        input_shape = self.model.input_shape
        target_h = int(input_shape[1]) if input_shape and input_shape[1] else 256
        target_w = int(input_shape[2]) if input_shape and input_shape[2] else 256
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (target_w, target_h), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
        pred = self.model.predict(np.expand_dims(resized, axis=0), verbose=0)[0]
        cls = np.argmax(pred, axis=-1).astype(np.uint8)
        road_mask = (cls == 1).astype(np.uint8) * 255
        lane_mask = (cls == 2).astype(np.uint8) * 255
        road_mask = cv2.resize(road_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        lane_mask = cv2.resize(lane_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return LaneMaskResult(
            road_mask=road_mask,
            lane_mask=lane_mask,
            confidence=float(np.max(pred)),
            metadata={
                "model": self.model_key,
                "repo_id": self.repo_id,
                "input_size": [target_w, target_h],
                "class_map": {"0": "background", "1": "road", "2": "lane_markings"},
            },
        )


def build_model(key: str, args: argparse.Namespace) -> LaneMaskModel:
    if key == "yolop":
        return YolopLaneModel(args.cache_dir, args.conf_threshold)
    if key == "segformer-cityscapes":
        return SegFormerCityscapesModel(EXECUTABLE_MODELS[key]["repo_id"], args.cache_dir)
    if key == "keras-road-lane":
        return KerasRoadLaneModel(EXECUTABLE_MODELS[key]["repo_id"])
    raise KeyError(f"Model is not executable in this script: {key}")


def snapshot_download_model(repo_id: str, cache_dir: Path) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo_id=repo_id, cache_dir=cache_dir / "huggingface"))


def download_requested_models(model_keys: list[str], cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for key in model_keys:
        if key in EXECUTABLE_MODELS and "repo_id" in EXECUTABLE_MODELS[key]:
            path = snapshot_download_model(str(EXECUTABLE_MODELS[key]["repo_id"]), cache_dir)
            print(f"Downloaded {key}: {path}")
        elif key in DOWNLOAD_ONLY_MODELS:
            path = snapshot_download_model(str(DOWNLOAD_ONLY_MODELS[key]["repo_id"]), cache_dir)
            print(f"Downloaded {key}: {path}")
        elif key == "yolop":
            print("YOLOP downloads through torch.hub when inference starts.")
        else:
            raise KeyError(f"Unknown model key: {key}")


def trip_list(args: argparse.Namespace) -> list[Path]:
    from fleetiq_training_roadface.datasets import (
        discover_trip_dirs,
        resolve_trip_dir,
    )

    if args.trip.lower() == "all":
        return discover_trip_dirs(args.dataset)
    return [resolve_trip_dir(args.trip, args.dataset)]


def image_paths_for_trip(trip_dir: Path, args: argparse.Namespace) -> list[Path]:
    from fleetiq_training_roadface.experimental import find_image

    image_dir = trip_dir / "kitti" / "image_2"
    if args.frame is not None:
        path = find_image(image_dir, f"{args.frame:06d}")
        if path is None:
            raise FileNotFoundError(f"Frame {args.frame:06d} not found in {image_dir}")
        return [path]
    if args.frames:
        paths = []
        for frame in args.frames:
            path = find_image(image_dir, f"{frame:06d}")
            if path is None:
                raise FileNotFoundError(f"Frame {frame:06d} not found in {image_dir}")
            paths.append(path)
        return paths
    all_paths = sorted(
        path for path in image_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stem.isdigit()
    )
    if args.all_frames or len(all_paths) <= args.sample_count:
        return all_paths
    indices = np.linspace(0, len(all_paths) - 1, num=max(1, args.sample_count), dtype=int)
    return [all_paths[int(idx)] for idx in indices]


def write_result(
    base_dir: Path,
    trip_name: str,
    model_key: str,
    image_path: Path,
    image_bgr: np.ndarray,
    result: LaneMaskResult,
    args: argparse.Namespace,
) -> None:
    stem = image_path.stem
    model_dir = base_dir / trip_name / model_key
    road_dir = model_dir / "road_masks"
    lane_dir = model_dir / "lane_masks"
    overlay_dir = model_dir / "overlays"
    meta_dir = model_dir / "metadata"
    for directory in (road_dir, lane_dir, overlay_dir, meta_dir):
        directory.mkdir(parents=True, exist_ok=True)
    road_mask = normalize_mask(result.road_mask, image_bgr.shape[:2], close_px=args.road_close_px)
    lane_mask = normalize_mask(result.lane_mask, image_bgr.shape[:2], dilate_px=args.lane_dilate_px)
    if road_mask is not None:
        cv2.imwrite(str(road_dir / f"{stem}.png"), road_mask)
    if lane_mask is not None:
        cv2.imwrite(str(lane_dir / f"{stem}.png"), lane_mask)
    overlay = overlay_masks(image_bgr, road_mask, lane_mask, f"{trip_name} {stem} {model_key}")
    cv2.imwrite(str(overlay_dir / f"{stem}.png"), overlay)
    metadata = {
        **result.metadata,
        "trip": trip_name,
        "frame": int(stem),
        "source_image": str(image_path),
        "output": {
            "road_mask": str(road_dir / f"{stem}.png") if road_mask is not None else None,
            "lane_mask": str(lane_dir / f"{stem}.png") if lane_mask is not None else None,
            "overlay": str(overlay_dir / f"{stem}.png"),
        },
        "postprocess": {
            "conf_threshold": args.conf_threshold,
            "road_close_px": args.road_close_px,
            "lane_dilate_px": args.lane_dilate_px,
        },
    }
    (meta_dir / f"{stem}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.list_models:
        print_model_registry()
        return
    unknown = [key for key in args.models if key not in EXECUTABLE_MODELS and key not in DOWNLOAD_ONLY_MODELS]
    if unknown:
        raise KeyError(f"Unknown model keys: {unknown}. Run with --list-models.")
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    if args.download_only:
        download_requested_models(args.models, args.cache_dir)
        return

    download_only_requested = [key for key in args.models if key in DOWNLOAD_ONLY_MODELS]
    if download_only_requested:
        download_requested_models(download_only_requested, args.cache_dir)
        print(f"Skipped inference for download-only models: {download_only_requested}")
    executable_keys = [key for key in args.models if key in EXECUTABLE_MODELS]
    if not executable_keys:
        return
    if RUNTIME_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Install runtime image dependencies first, for example: "
            "uv sync --all-packages --extra cu130 --extra models"
        ) from RUNTIME_IMPORT_ERROR

    from fleetiq_training_roadface.experimental import read_image

    models = [build_model(key, args) for key in executable_keys]
    trips = trip_list(args)
    if not trips:
        raise FileNotFoundError(f"No trips found for dataset={args.dataset!r}")
    for trip_dir in trips:
        images = image_paths_for_trip(trip_dir, args)
        print(f"{trip_dir.name}: processing {len(images)} frame(s)")
        for image_path in images:
            image = read_image(image_path)
            if image is None:
                print(f"  skip unreadable image: {image_path}")
                continue
            for model in models:
                result = model.predict(image)
                write_result(args.output_dir, trip_dir.name, model.model_key, image_path, image, result, args)
                print(f"  wrote {model.model_key} masks for {trip_dir.name}/{image_path.stem}")


if __name__ == "__main__":
    main()
