from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

from fleetiq_training_roadface.experimental import (
    CLASS_COLORS,
    discover_trips,
    draw_tag,
    find_image,
    read_image,
    valid_bbox,
)


OUTPUT_LABEL_DIR = "label2_yolop"
BDD13_FALLBACK = [
    "person",
    "rider",
    "car",
    "bus",
    "truck",
    "bike",
    "motor",
    "tl_green",
    "tl_red",
    "tl_yellow",
    "tl_none",
    "traffic sign",
    "train",
]
BDD10_FALLBACK = [
    "bike",
    "bus",
    "car",
    "motor",
    "person",
    "rider",
    "traffic light",
    "traffic sign",
    "train",
    "truck",
]
BDD4_VEHICLE_FALLBACK = ["car", "bus", "truck", "train"]


@dataclass(frozen=True)
class YolopObject:
    object_type: str
    bbox: tuple[float, float, float, float]
    confidence: float
    raw_class: str


@dataclass(frozen=True)
class YolopFrameResult:
    road_mask: np.ndarray
    lane_mask: np.ndarray
    objects: list[YolopObject]
    elapsed_s: float
    metadata: dict[str, object]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run YOLOP once per image_2 frame, save drivable/lane masks and "
            "KITTI-format traffic-object labels to kitti/label2_yolop."
        )
    )
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--dataset-root", type=Path, help="Override dataset root containing trip folders.")
    parser.add_argument("--trip", action="append", help="Trip id. Repeat or omit for all trips.")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--frame", type=int, help="Single frame id.")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--max-det", type=int, default=80)
    parser.add_argument("--label-dir-name", default=OUTPUT_LABEL_DIR)
    parser.add_argument("--overwrite", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--device", default="auto", help="'auto', 'cpu', 'cuda', or a CUDA device like 'cuda:0'.")
    parser.add_argument("--cache-dir", type=Path, default=Path("artifacts/model_cache"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/roadface/yolop_panoptic"),
        help="Stores masks, overlays, and metadata. KITTI labels are always written under each trip/kitti.",
    )
    parser.add_argument("--save-masks", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--save-overlays", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--visualize", choices=("none", "window", "video", "gif"), default="none")
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument(
        "--window-name",
        default="FleetIQ YOLOP road/lane/vehicle",
        help="OpenCV window title when --visualize window.",
    )
    parser.add_argument("--class-names", help="Comma-separated detector class names when YOLOP does not expose names.")
    parser.add_argument(
        "--keep-traffic-control",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Keep traffic light/sign in raw metadata only by default; KITTI label_2 consumers here ignore them.",
    )
    parser.add_argument("--manifest-only", action="store_true")
    return parser.parse_args()


def dataset_key_or_root(args: argparse.Namespace) -> str:
    return str(args.dataset_root) if args.dataset_root is not None else args.dataset


def selected_trips(args: argparse.Namespace) -> list[Path]:
    trips = discover_trips(dataset_key_or_root(args))
    requested = set(args.trip or [])
    selected = [trip for trip in trips if not requested or trip.name in requested]
    if not selected:
        available = ", ".join(trip.name for trip in trips)
        raise SystemExit(f"No matching trips. Available: {available}")
    return selected


def selected_images(trip_dir: Path, args: argparse.Namespace) -> list[Path]:
    image_dir = trip_dir / "kitti" / "image_2"
    if args.frame is not None:
        image = find_image(image_dir, f"{args.frame:06d}")
        if image is None:
            raise FileNotFoundError(f"Missing frame {args.frame:06d} in {image_dir}")
        return [image]
    images = [
        path
        for path in sorted(image_dir.iterdir())
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stem.isdigit()
    ]
    selected = [
        path
        for path in images
        if int(path.stem) >= args.start
        and (args.end is None or int(path.stem) <= args.end)
        and (int(path.stem) - args.start) % max(1, args.stride) == 0
    ]
    return selected[: args.max_frames] if args.max_frames is not None else selected


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def kitti_2d_line(obj: YolopObject) -> str:
    x1, y1, x2, y2 = obj.bbox
    return (
        f"{obj.object_type} 0.00 0 -10.00 "
        f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f} "
        f"-1.00 -1.00 -1.00 -1000.00 -1000.00 -1000.00 -10.00 {obj.confidence:.4f}"
    )


def normalize_class_name(raw: str) -> str:
    return raw.strip().lower().replace("_", " ")


def canonical_kitti_type(raw_name: str, keep_traffic_control: bool = False) -> str | None:
    name = normalize_class_name(raw_name)
    if name in {"0", "vehicle", "vehicles"}:
        return "Car"
    if name in {"car", "auto", "automobile"}:
        return "Car"
    if name in {"bus", "coach"}:
        return "Bus"
    if name in {"truck", "lorry"}:
        return "Truck"
    if name in {"train", "trailer", "caravan", "long vehicle"}:
        return "LongVehicle"
    if name in {"motor", "motorbike", "motorcycle", "scooter"}:
        return "Motorcycle"
    if name in {"bike", "bicycle", "cyclist", "rider"}:
        return "Cyclist"
    if name in {"person", "pedestrian"}:
        return "Pedestrian"
    if keep_traffic_control and name.startswith("traffic"):
        return None
    return None


def xywh_to_xyxy(boxes: object) -> object:
    y = boxes.clone()
    y[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
    y[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
    y[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
    y[:, 3] = boxes[:, 1] + boxes[:, 3] / 2
    return y


def bbox_iou_torch(box: object, boxes: object) -> object:
    inter_x1 = boxes[:, 0].clamp(min=float(box[0]))
    inter_y1 = boxes[:, 1].clamp(min=float(box[1]))
    inter_x2 = boxes[:, 2].clamp(max=float(box[2]))
    inter_y2 = boxes[:, 3].clamp(max=float(box[3]))
    inter = (inter_x2 - inter_x1).clamp(min=0) * (inter_y2 - inter_y1).clamp(min=0)
    area_a = (box[2] - box[0]).clamp(min=0) * (box[3] - box[1]).clamp(min=0)
    area_b = (boxes[:, 2] - boxes[:, 0]).clamp(min=0) * (boxes[:, 3] - boxes[:, 1]).clamp(min=0)
    return inter / (area_a + area_b - inter + 1e-6)


def nms_pure_torch(boxes: object, scores: object, iou_threshold: float, max_det: int) -> object:
    torch = sys.modules["torch"]
    keep: list[object] = []
    order = scores.argsort(descending=True)
    while order.numel() > 0 and len(keep) < max_det:
        idx = order[0]
        keep.append(idx)
        if order.numel() == 1:
            break
        ious = bbox_iou_torch(boxes[idx], boxes[order[1:]])
        order = order[1:][ious <= iou_threshold]
    if not keep:
        return torch.empty((0,), dtype=torch.long, device=boxes.device)
    return torch.stack(keep).long()


def nms_yolov5_style(prediction: object, conf_thres: float, iou_thres: float, max_det: int) -> list[object]:
    torch = sys.modules["torch"]
    if isinstance(prediction, (list, tuple)):
        prediction = prediction[0]
    if prediction.ndim == 2:
        prediction = prediction.unsqueeze(0)
    outputs: list[object] = []
    for x in prediction:
        if x.numel() == 0 or x.shape[1] < 6:
            outputs.append(torch.empty((0, 6), device=x.device))
            continue
        x = x[x[:, 4] > conf_thres]
        if not x.shape[0]:
            outputs.append(torch.empty((0, 6), device=x.device))
            continue
        class_scores, class_ids = x[:, 5:].max(1)
        scores = x[:, 4] * class_scores
        keep_conf = scores > conf_thres
        x = x[keep_conf]
        scores = scores[keep_conf]
        class_ids = class_ids[keep_conf].float()
        if not x.shape[0]:
            outputs.append(torch.empty((0, 6), device=x.device))
            continue
        boxes = xywh_to_xyxy(x[:, :4])
        keep = nms_pure_torch(boxes, scores, iou_thres, max_det)
        outputs.append(torch.cat((boxes[keep], scores[keep, None], class_ids[keep, None]), dim=1))
    return outputs


def class_names_from_model(model: object, output_class_count: int, override: str | None) -> list[str]:
    if override:
        names = [name.strip() for name in override.split(",") if name.strip()]
        if len(names) != output_class_count:
            raise ValueError(f"--class-names has {len(names)} names, but detector output has {output_class_count} classes.")
        return names
    names_obj = getattr(model, "names", None)
    if isinstance(names_obj, dict):
        names = [str(names_obj.get(i, i)) for i in range(output_class_count)]
        if len(names) == output_class_count and names != [str(i) for i in range(output_class_count)]:
            return names
    if (
        isinstance(names_obj, (list, tuple))
        and len(names_obj) == output_class_count
        and list(map(str, names_obj)) != [str(i) for i in range(output_class_count)]
    ):
        return [str(name) for name in names_obj]
    if output_class_count == 1:
        return ["vehicle"]
    if output_class_count == 4:
        return BDD4_VEHICLE_FALLBACK
    if output_class_count == 10:
        return BDD10_FALLBACK
    if output_class_count == 13:
        return BDD13_FALLBACK
    return [str(index) for index in range(output_class_count)]


def mask_from_segmentation(
    output: object,
    original_shape_hw: tuple[int, int],
    network_shape_hw: tuple[int, int],
    ratio: tuple[float, float],
    pad: tuple[float, float],
) -> tuple[np.ndarray, float]:
    torch = sys.modules["torch"]
    if isinstance(output, (list, tuple)):
        output = output[0]
    logits = output.detach()
    if logits.ndim == 3:
        logits = logits.unsqueeze(0)
    if logits.shape[1] == 1:
        score = torch.sigmoid(logits[:, 0])
    else:
        score = logits[:, 1]
        score = torch.where(score > logits[:, 0], score, torch.zeros_like(score))
    score_np = score[0].float().cpu().numpy()
    net_h, net_w = network_shape_hw
    pad_w, pad_h = int(round(pad[0])), int(round(pad[1]))
    y1 = max(0, pad_h)
    y2 = max(y1 + 1, net_h - pad_h)
    x1 = max(0, pad_w)
    x2 = max(x1 + 1, net_w - pad_w)
    if score_np.shape[:2] != (net_h, net_w):
        score_np = cv2.resize(score_np, (net_w, net_h), interpolation=cv2.INTER_LINEAR)
    score_np = score_np[y1:y2, x1:x2]
    h, w = original_shape_hw
    score_np = cv2.resize(score_np, (w, h), interpolation=cv2.INTER_LINEAR)
    return (score_np >= 0.5).astype(np.uint8) * 255, float(np.nanmean(score_np))


def letterbox_for_img(
    image_bgr: np.ndarray,
    new_shape: int,
    color: tuple[int, int, int] = (114, 114, 114),
    auto: bool = True,
) -> tuple[np.ndarray, tuple[float, float], tuple[float, float]]:
    shape = image_bgr.shape[:2]
    target = (new_shape, new_shape)
    r = min(target[0] / shape[0], target[1] / shape[1])
    ratio = (r, r)
    new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
    dw = target[1] - new_unpad[0]
    dh = target[0] - new_unpad[1]
    if auto:
        dw, dh = np.mod(dw, 32), np.mod(dh, 32)
    dw /= 2
    dh /= 2
    if shape[::-1] != new_unpad:
        image_bgr = cv2.resize(image_bgr, new_unpad, interpolation=cv2.INTER_AREA)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    padded = cv2.copyMakeBorder(image_bgr, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return padded, ratio, (dw, dh)


def scale_boxes_to_original(
    boxes: np.ndarray,
    original_shape_hw: tuple[int, int],
    ratio: tuple[float, float],
    pad: tuple[float, float],
) -> np.ndarray:
    scaled = boxes.copy()
    scaled[:, [0, 2]] -= pad[0]
    scaled[:, [1, 3]] -= pad[1]
    scaled[:, [0, 2]] /= ratio[0]
    scaled[:, [1, 3]] /= ratio[1]
    h, w = original_shape_hw
    scaled[:, [0, 2]] = np.clip(scaled[:, [0, 2]], 0, w - 1)
    scaled[:, [1, 3]] = np.clip(scaled[:, [1, 3]], 0, h - 1)
    return scaled


def postprocess_mask(mask: np.ndarray, mode: str) -> np.ndarray:
    if mode == "road":
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.dilate(mask, kernel, iterations=1)


class YolopPanopticModel:
    def __init__(self, args: argparse.Namespace) -> None:
        import torch

        self.torch = torch
        os.environ.setdefault("TORCH_HOME", str((args.cache_dir / "torch").resolve()))
        if args.device == "auto":
            self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(args.device)
        self.imgsz = int(args.imgsz)
        self.conf = float(args.conf)
        self.iou = float(args.iou)
        self.max_det = int(args.max_det)
        self.class_name_override = args.class_names
        self.keep_traffic_control = bool(args.keep_traffic_control)
        self.model = torch.hub.load("hustvl/yolop", "yolop", pretrained=True)
        self.model.to(self.device).eval()

    def _preprocess(self, image_bgr: np.ndarray) -> tuple[object, tuple[int, int], tuple[float, float], tuple[float, float]]:
        padded, ratio, pad = letterbox_for_img(image_bgr, self.imgsz, auto=True)
        array = padded.astype(np.float32) / 255.0
        mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
        array = (array - mean) / std
        tensor = self.torch.from_numpy(array).permute(2, 0, 1).float().unsqueeze(0)
        return tensor.to(self.device), padded.shape[:2], ratio, pad

    def predict(self, image_bgr: np.ndarray) -> YolopFrameResult:
        started = time.perf_counter()
        h, w = image_bgr.shape[:2]
        input_tensor, network_shape, ratio, pad = self._preprocess(image_bgr)
        with self.torch.inference_mode():
            det_out, road_out, lane_out = self.model(input_tensor)
        det_tensor = det_out[0] if isinstance(det_out, (tuple, list)) else det_out
        output_class_count = max(1, int(det_tensor.shape[-1]) - 5)
        class_names = class_names_from_model(self.model, output_class_count, self.class_name_override)
        det = nms_yolov5_style(det_tensor, self.conf, self.iou, self.max_det)[0].detach().cpu().numpy()
        objects: list[YolopObject] = []
        if det.size:
            det[:, :4] = scale_boxes_to_original(det[:, :4], (h, w), ratio, pad)
        for row in det:
            x1, y1, x2, y2, confidence, cls_id = row.tolist()
            bbox = valid_bbox((x1, y1, x2, y2), w, h)
            if bbox is None:
                continue
            raw_class = class_names[int(cls_id)] if int(cls_id) < len(class_names) else str(int(cls_id))
            object_type = canonical_kitti_type(raw_class, self.keep_traffic_control)
            if object_type is None:
                continue
            objects.append(
                YolopObject(
                    object_type=object_type,
                    bbox=bbox,
                    confidence=float(confidence),
                    raw_class=raw_class,
                )
            )
        road_mask, road_conf = mask_from_segmentation(road_out, (h, w), network_shape, ratio, pad)
        lane_mask, lane_conf = mask_from_segmentation(lane_out, (h, w), network_shape, ratio, pad)
        road_mask = postprocess_mask(road_mask, "road")
        lane_mask = postprocess_mask(lane_mask, "lane")
        elapsed = time.perf_counter() - started
        return YolopFrameResult(
            road_mask=road_mask,
            lane_mask=lane_mask,
            objects=objects,
            elapsed_s=float(elapsed),
            metadata={
                "device": str(self.device),
                "imgsz": self.imgsz,
                "conf": self.conf,
                "iou": self.iou,
                "class_names": class_names,
                "network_shape_hw": list(network_shape),
                "letterbox_ratio": list(ratio),
                "letterbox_pad": list(pad),
                "road_score_mean": road_conf,
                "lane_score_mean": lane_conf,
            },
        )


def draw_yolop_overlay(image_bgr: np.ndarray, result: YolopFrameResult, caption: str) -> np.ndarray:
    output = image_bgr.copy()
    road_color = np.zeros_like(output)
    road_color[:, :, 1] = 180
    output = np.where(result.road_mask[:, :, None] > 0, cv2.addWeighted(output, 0.75, road_color, 0.25, 0), output)
    lane_color = np.zeros_like(output)
    lane_color[:, :, 1] = 230
    lane_color[:, :, 2] = 255
    output = np.where(result.lane_mask[:, :, None] > 0, lane_color, output)
    for obj in result.objects:
        color = CLASS_COLORS.get(obj.object_type, (220, 220, 220))
        x1, y1, x2, y2 = [int(round(v)) for v in obj.bbox]
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        draw_tag(output, f"{obj.object_type} {obj.confidence:.2f}", (x1, max(18, y1 - 4)), color)
    cv2.rectangle(output, (0, output.shape[0] - 28), (output.shape[1], output.shape[0]), (20, 25, 30), -1)
    cv2.putText(
        output,
        f"{caption} | yolop objects={len(result.objects)}",
        (10, output.shape[0] - 9),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (240, 240, 240),
        1,
        cv2.LINE_AA,
    )
    return output


def append_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def write_outputs(
    trip_dir: Path,
    image_path: Path,
    image_bgr: np.ndarray,
    result: YolopFrameResult,
    args: argparse.Namespace,
) -> None:
    stem = image_path.stem
    label_dir = trip_dir / "kitti" / args.label_dir_name
    label_path = label_dir / f"{stem}.txt"
    if args.overwrite or not label_path.exists():
        label_text = "\n".join(kitti_2d_line(obj) for obj in result.objects)
        if label_text:
            label_text += "\n"
        atomic_write_text(label_path, label_text)

    artifact_root = args.output_dir / trip_dir.name
    metadata = {
        "trip": trip_dir.name,
        "frame": int(stem),
        "source_image": str(image_path),
        "label_path": str(label_path),
        "elapsed_s": round(result.elapsed_s, 4),
        "objects": [asdict(obj) for obj in result.objects],
        "model": result.metadata,
    }
    if args.save_masks:
        road_dir = artifact_root / "road_masks"
        lane_dir = artifact_root / "lane_masks"
        road_dir.mkdir(parents=True, exist_ok=True)
        lane_dir.mkdir(parents=True, exist_ok=True)
        road_path = road_dir / f"{stem}.png"
        lane_path = lane_dir / f"{stem}.png"
        cv2.imwrite(str(road_path), result.road_mask)
        cv2.imwrite(str(lane_path), result.lane_mask)
        metadata["road_mask"] = str(road_path)
        metadata["lane_mask"] = str(lane_path)
    if args.save_overlays:
        overlay_dir = artifact_root / "overlays"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        overlay_path = overlay_dir / f"{stem}.png"
        overlay = draw_yolop_overlay(image_bgr, result, f"{trip_dir.name} frame {stem}")
        cv2.imwrite(str(overlay_path), overlay)
        metadata["overlay"] = str(overlay_path)
    metadata_path = artifact_root / "metadata" / f"{stem}.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    append_jsonl(artifact_root / "_yolop_panoptic.jsonl", metadata)


def outputs_ready(trip_dir: Path, image_path: Path, args: argparse.Namespace) -> bool:
    stem = image_path.stem
    artifact_root = args.output_dir / trip_dir.name
    required = [
        trip_dir / "kitti" / args.label_dir_name / f"{stem}.txt",
        artifact_root / "metadata" / f"{stem}.json",
    ]
    if args.save_masks:
        required.extend(
            [
                artifact_root / "road_masks" / f"{stem}.png",
                artifact_root / "lane_masks" / f"{stem}.png",
            ]
        )
    if args.save_overlays:
        required.append(artifact_root / "overlays" / f"{stem}.png")
    return all(path.exists() for path in required)


class Visualizer:
    def __init__(self, trip_dir: Path, args: argparse.Namespace) -> None:
        self.mode = args.visualize
        self.args = args
        self.trip_dir = trip_dir
        self.writer = None
        self.gif_writer = None
        if self.mode == "window":
            cv2.namedWindow(args.window_name, cv2.WINDOW_NORMAL)
        if self.mode == "gif":
            try:
                import imageio.v2 as imageio
            except ImportError as exc:
                raise RuntimeError("Install roadface deps with imageio before using --visualize gif.") from exc
            gif_path = args.output_dir / trip_dir.name / f"{trip_dir.name}_yolop_panoptic.gif"
            gif_path.parent.mkdir(parents=True, exist_ok=True)
            self.gif_writer = imageio.get_writer(str(gif_path), mode="I", duration=1.0 / max(args.fps, 1.0))
            print(f"Writing GIF visualization: {gif_path}")

    def update(self, frame_bgr: np.ndarray) -> bool:
        if self.mode == "none":
            return True
        if self.mode == "window":
            cv2.imshow(self.args.window_name, frame_bgr)
            key = cv2.waitKey(max(1, int(1000 / max(self.args.fps, 1.0)))) & 0xFF
            return key not in (27, ord("q"))
        if self.mode == "video":
            if self.writer is None:
                h, w = frame_bgr.shape[:2]
                video_path = self.args.output_dir / self.trip_dir.name / f"{self.trip_dir.name}_yolop_panoptic.mp4"
                video_path.parent.mkdir(parents=True, exist_ok=True)
                self.writer = cv2.VideoWriter(
                    str(video_path),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    self.args.fps,
                    (w, h),
                )
                print(f"Writing video visualization: {video_path}")
            self.writer.write(frame_bgr)
            return True
        if self.mode == "gif":
            assert self.gif_writer is not None
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            self.gif_writer.append_data(rgb)
        return True

    def close(self) -> None:
        if self.writer is not None:
            self.writer.release()
        if self.gif_writer is not None:
            self.gif_writer.close()
        if self.mode == "window":
            cv2.destroyWindow(self.args.window_name)


def run_trip(model: YolopPanopticModel, trip_dir: Path, args: argparse.Namespace) -> tuple[int, int]:
    images = selected_images(trip_dir, args)
    processed = 0
    skipped = 0
    visualizer = Visualizer(trip_dir, args)
    try:
        for image_path in images:
            if outputs_ready(trip_dir, image_path, args) and not args.overwrite and args.visualize == "none":
                skipped += 1
                continue
            image = read_image(image_path)
            if image is None:
                skipped += 1
                continue
            result = model.predict(image)
            write_outputs(trip_dir, image_path, image, result, args)
            overlay = draw_yolop_overlay(image, result, f"{trip_dir.name} frame {image_path.stem}")
            if not visualizer.update(overlay):
                break
            processed += 1
            if processed == 1 or processed % 50 == 0:
                print(f"{trip_dir.name}: labeled={processed} skipped={skipped} frame={image_path.stem} objects={len(result.objects)}")
    finally:
        visualizer.close()
    return processed, skipped


def main() -> None:
    args = parse_args()
    trips = selected_trips(args)
    counts = [(trip, len(selected_images(trip, args))) for trip in trips]
    total = sum(count for _, count in counts)
    print(f"Selected {len(trips)} trip(s), {total} image_2 frame(s)")
    for trip, count in counts:
        print(f"  {trip.name}: {count}")
    if args.manifest_only:
        return
    model = YolopPanopticModel(args)
    total_processed = 0
    total_skipped = 0
    for trip, _ in counts:
        processed, skipped = run_trip(model, trip, args)
        total_processed += processed
        total_skipped += skipped
    print(
        f"Finished: labeled={total_processed} skipped={total_skipped} "
        f"labels=kitti/{args.label_dir_name} artifacts={args.output_dir}"
    )


if __name__ == "__main__":
    main()
