from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import cv2
import numpy as np

from fleetiq_training_roadface.experimental import (
    PlaneLaneEstimate,
    compute_road_and_lane,
    detections_from_labels,
    detections_ignore_mask,
    discover_trips,
    draw_overlay,
    estimate_plane_lane,
    find_image,
    finite_or_none,
    load_gt_depth,
    load_trip_doc,
    parse_calibration,
    read_image,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit plane-based lane estimation on evenly sampled practice frames.")
    parser.add_argument("--dataset", choices=("practice", "redacted", "all"), default="practice")
    parser.add_argument("--frames-per-trip", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/roadface/plane_lane_audit"))
    parser.add_argument("--depth-policy", choices=("previous", "nearest"), default="nearest")
    parser.add_argument("--lane-width-m", type=float, default=3.7)
    parser.add_argument("--lookahead-m", type=float, default=10.0)
    parser.add_argument("--render", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def evenly_sample_frame_ids(trip_dir: Path, count: int) -> list[int]:
    frames = load_trip_doc(trip_dir).get("frames", [])
    ids = [int(frame.get("frame_id", idx)) for idx, frame in enumerate(frames)]
    if not ids:
        image_ids = sorted(int(path.stem) for path in (trip_dir / "kitti" / "image_2").glob("*.*") if path.stem.isdigit())
        ids = image_ids
    if len(ids) <= count:
        return ids
    positions = np.linspace(0, len(ids) - 1, count)
    return [ids[int(round(pos))] for pos in positions]


def band_width(mask: np.ndarray, y_frac: float) -> tuple[int, float]:
    h, w = mask.shape[:2]
    y = int(np.clip(round(y_frac * (h - 1)), 0, h - 1))
    xs = np.where(mask[y] > 0)[0]
    if xs.size == 0:
        return 0, math.nan
    return int(xs.max() - xs.min() + 1), float((xs.min() + xs.max()) / 2.0 / max(w - 1, 1))


def score_range(value: float, good_max: float, bad_max: float) -> float:
    value = abs(value)
    if not math.isfinite(value):
        return 0.0
    if value <= good_max:
        return 1.0
    if value >= bad_max:
        return 0.0
    return 1.0 - (value - good_max) / max(bad_max - good_max, 1e-6)


def score_interval(value: float, good_lo: float, good_hi: float, bad_lo: float, bad_hi: float) -> float:
    if not math.isfinite(value):
        return 0.0
    if good_lo <= value <= good_hi:
        return 1.0
    if value < good_lo:
        if value <= bad_lo:
            return 0.0
        return (value - bad_lo) / max(good_lo - bad_lo, 1e-6)
    if value >= bad_hi:
        return 0.0
    return 1.0 - (value - good_hi) / max(bad_hi - good_hi, 1e-6)


def score_estimate(est: PlaneLaneEstimate) -> tuple[float, str, dict[str, float]]:
    h, w = est.corridor_mask.shape[:2]
    area_ratio = float(np.count_nonzero(est.corridor_mask) / max(h * w, 1))
    near_w_px, near_center = band_width(est.corridor_mask, 0.92)
    mid_w_px, mid_center = band_width(est.corridor_mask, 0.70)
    far_w_px, far_center = band_width(est.corridor_mask, 0.54)
    near_ratio = near_w_px / max(w, 1)
    mid_ratio = mid_w_px / max(w, 1)
    far_ratio = far_w_px / max(w, 1)

    metrics = {
        "plane": score_interval(est.plane.inlier_ratio, 0.55, 1.00, 0.15, 1.00),
        "conf": float(np.clip(est.confidence, 0.0, 1.0)),
        "area": score_interval(area_ratio, 0.10, 0.38, 0.03, 0.55),
        "near_width": score_interval(near_ratio, 0.32, 0.80, 0.16, 0.98),
        "mid_width": score_interval(mid_ratio, 0.18, 0.62, 0.08, 0.80),
        "far_width": score_interval(far_ratio, 0.04, 0.35, 0.00, 0.50),
        "offset": score_range(est.lane_offset_m, 0.35, 1.30),
        "heading": score_range(est.heading_deg, 4.0, 12.0),
    }
    weighted = (
        16 * metrics["plane"]
        + 18 * metrics["conf"]
        + 12 * metrics["area"]
        + 12 * metrics["near_width"]
        + 10 * metrics["mid_width"]
        + 8 * metrics["far_width"]
        + 14 * metrics["offset"]
        + 10 * metrics["heading"]
    )
    issues: list[str] = []
    if est.plane.inlier_ratio < 0.55:
        issues.append("weak_plane")
    if area_ratio < 0.08 or area_ratio > 0.45:
        issues.append("bad_area")
    if near_ratio < 0.28 or near_ratio > 0.90:
        issues.append("bad_near_width")
    if abs(est.lane_offset_m) > 0.75:
        issues.append("large_offset")
    if abs(est.heading_deg) > 8.0:
        issues.append("large_heading")
    if not issues:
        issues.append("ok")
    return float(np.clip(weighted, 0.0, 100.0)), ";".join(issues), {
        "area_ratio": area_ratio,
        "near_width_ratio": near_ratio,
        "mid_width_ratio": mid_ratio,
        "far_width_ratio": far_ratio,
        "near_center_ratio": near_center,
        "mid_center_ratio": mid_center,
        "far_center_ratio": far_center,
    }


def render_audit_frame(image: np.ndarray, est: PlaneLaneEstimate, trip: str, frame_id: int, score: float, issues: str) -> np.ndarray:
    overlay = draw_overlay(
        image,
        [],
        est.road_mask,
        est.lane_mask,
        est.lane_offset_m,
        corridor_mask=est.corridor_mask,
        vertical_corridor_mask=est.vertical_corridor_mask,
    )
    panel_h = 92
    panel = np.full((panel_h, overlay.shape[1], 3), (28, 38, 48), dtype=np.uint8)
    rows = [
        f"{trip} frame {frame_id:06d} score={score:.1f} issues={issues}",
        f"offset={est.lane_offset_m:+.2f}m heading={est.heading_deg:+.2f}deg conf={est.confidence:.2f}",
        f"plane={est.plane.source} inliers={est.plane.inlier_count} ratio={est.plane.inlier_ratio:.2f} {est.note}",
    ]
    for idx, row in enumerate(rows):
        cv2.putText(panel, row, (14, 24 + idx * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (236, 242, 248), 1, cv2.LINE_AA)
    return np.vstack([overlay, panel])


def make_contact_sheet(paths: list[Path], output: Path, tile_w: int = 320) -> None:
    images = [cv2.imread(str(path)) for path in paths]
    images = [image for image in images if image is not None]
    if not images:
        return
    tiles: list[np.ndarray] = []
    for image in images:
        scale = tile_w / image.shape[1]
        tiles.append(cv2.resize(image, (tile_w, int(image.shape[0] * scale)), interpolation=cv2.INTER_AREA))
    tile_h = max(tile.shape[0] for tile in tiles)
    padded = []
    for tile in tiles:
        canvas = np.full((tile_h, tile_w, 3), (18, 24, 32), dtype=np.uint8)
        canvas[: tile.shape[0], : tile.shape[1]] = tile
        padded.append(canvas)
    rows = []
    for idx in range(0, len(padded), 5):
        rows.append(np.hstack(padded[idx : idx + 5]))
    sheet = np.vstack(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), sheet)


def main() -> None:
    args = parse_args()
    out_dir = args.output_dir.resolve()
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    rendered_paths: list[Path] = []
    for trip_dir in discover_trips(args.dataset):
        for frame_id in evenly_sample_frame_ids(trip_dir, args.frames_per_trip):
            stem = f"{frame_id:06d}"
            image = read_image(find_image(trip_dir / "kitti" / "image_2", stem))
            if image is None:
                continue
            calibration = parse_calibration(trip_dir / "kitti" / "calib" / f"{stem}.txt")
            depth = load_gt_depth(trip_dir, frame_id, args.depth_policy)
            road_mask, _, _, _ = compute_road_and_lane(image)
            detections = detections_from_labels(trip_dir / "kitti" / "label_2" / f"{stem}.txt", calibration, image.shape)
            ignore_mask = detections_ignore_mask(image.shape, detections) if detections else None
            est = estimate_plane_lane(
                image,
                depth,
                calibration,
                road_mask=road_mask,
                lane_mask=None,
                ignore_mask=ignore_mask,
                lane_width_m=args.lane_width_m,
                lookahead_m=args.lookahead_m,
            )
            score, issues, extra = score_estimate(est)
            rows.append(
                {
                    "trip": trip_dir.name,
                    "frame_id": frame_id,
                    "score": round(score, 2),
                    "issues": issues,
                    "offset_m": finite_or_none(est.lane_offset_m),
                    "heading_deg": finite_or_none(est.heading_deg),
                    "confidence": round(est.confidence, 4),
                    "plane_source": est.plane.source,
                    "plane_inlier_ratio": round(est.plane.inlier_ratio, 4),
                    "plane_inlier_count": est.plane.inlier_count,
                    "note": est.note,
                    **{key: round(value, 4) if math.isfinite(value) else "" for key, value in extra.items()},
                }
            )
            if args.render:
                rendered = render_audit_frame(image, est, trip_dir.name, frame_id, score, issues)
                path = frames_dir / f"{trip_dir.name}_{stem}_score_{score:05.1f}.png"
                cv2.imwrite(str(path), rendered)
                rendered_paths.append(path)

    csv_path = out_dir / "plane_lane_audit.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    summary_path = out_dir / "plane_lane_audit_summary.md"
    by_trip: dict[str, list[float]] = {}
    for row in rows:
        by_trip.setdefault(str(row["trip"]), []).append(float(row["score"]))
    lines = ["# Plane lane audit summary", ""]
    lines.append(f"Frames audited: {len(rows)}")
    lines.append("")
    lines.append("| trip | frames | avg | min | max |")
    lines.append("|---|---:|---:|---:|---:|")
    for trip, scores in sorted(by_trip.items()):
        lines.append(f"| {trip} | {len(scores)} | {np.mean(scores):.1f} | {np.min(scores):.1f} | {np.max(scores):.1f} |")
    lines.append("")
    lines.append("Worst frames:")
    for row in sorted(rows, key=lambda item: float(item["score"]))[:10]:
        lines.append(f"- {row['trip']} frame {int(row['frame_id']):06d}: score={float(row['score']):.1f}, issues={row['issues']}")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    make_contact_sheet(rendered_paths, out_dir / "plane_lane_contact_sheet.png")
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {out_dir / 'plane_lane_contact_sheet.png'}")


if __name__ == "__main__":
    main()
