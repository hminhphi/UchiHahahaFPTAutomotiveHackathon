"""Object association, frame-delta relative speed, and TTC."""

from __future__ import annotations

from dataclasses import dataclass

from .types import Detection, TrackedObstacle


@dataclass(slots=True)
class _DistanceSample:
    timestamp_s: float
    distance_m: float
    relative_speed_mps: float | None = None


@dataclass(slots=True)
class _Track:
    object_type: str
    bbox: tuple[float, float, float, float]
    timestamp_s: float
    distance_m: float | None
    missed: int = 0


class ClosingSpeedEstimator:
    """Estimate closing speed from distance change over the true frame delta."""

    def __init__(
        self,
        *,
        smoothing_alpha: float = 0.45,
        minimum_closing_speed_mps: float = 0.25,
    ) -> None:
        if not 0.0 < smoothing_alpha <= 1.0:
            raise ValueError("smoothing_alpha must be in (0, 1]")
        self.smoothing_alpha = smoothing_alpha
        self.minimum_closing_speed_mps = minimum_closing_speed_mps
        self._samples: dict[int, _DistanceSample] = {}

    def update(
        self,
        *,
        track_id: int,
        timestamp_s: float,
        distance_m: float,
    ) -> TrackedObstacle:
        previous = self._samples.get(track_id)
        relative_speed_mps: float | None = None
        if previous is not None:
            frame_delta_s = timestamp_s - previous.timestamp_s
            if frame_delta_s <= 0.0:
                return TrackedObstacle(
                    track_id=track_id,
                    timestamp_s=timestamp_s,
                    distance_m=distance_m,
                )
            measured = (previous.distance_m - distance_m) / frame_delta_s
            relative_speed_mps = measured
            if previous.relative_speed_mps is not None:
                relative_speed_mps = (
                    self.smoothing_alpha * measured
                    + (1.0 - self.smoothing_alpha) * previous.relative_speed_mps
                )
        ttc_s = None
        if (
            relative_speed_mps is not None
            and relative_speed_mps > self.minimum_closing_speed_mps
            and distance_m > 0.0
        ):
            ttc_s = distance_m / relative_speed_mps
        self._samples[track_id] = _DistanceSample(
            timestamp_s=timestamp_s,
            distance_m=distance_m,
            relative_speed_mps=relative_speed_mps,
        )
        return TrackedObstacle(
            track_id=track_id,
            timestamp_s=timestamp_s,
            distance_m=distance_m,
            relative_speed_mps=relative_speed_mps,
            ttc_s=ttc_s,
        )

    def discard(self, track_id: int) -> None:
        self._samples.pop(track_id, None)


class ObstacleTracker:
    """Small deterministic IoU tracker with causal motion attachment."""

    def __init__(
        self,
        *,
        max_missed: int = 10,
        iou_threshold: float = 0.08,
        smoothing_alpha: float = 0.45,
        maximum_association_speed_mps: float = 45.0,
    ) -> None:
        self.max_missed = max_missed
        self.iou_threshold = iou_threshold
        self.maximum_association_speed_mps = maximum_association_speed_mps
        self.next_id = 1
        self.tracks: dict[int, _Track] = {}
        self.motion = ClosingSpeedEstimator(smoothing_alpha=smoothing_alpha)

    def update(
        self,
        detections: list[Detection],
        timestamp_s: float,
    ) -> list[Detection]:
        unmatched_tracks = set(self.tracks)
        for detection in sorted(
            detections,
            key=lambda item: item.bbox[2] - item.bbox[0],
            reverse=True,
        ):
            track_id = self._match(detection, unmatched_tracks, timestamp_s)
            if track_id is None:
                track_id = self.next_id
                self.next_id += 1
            else:
                unmatched_tracks.discard(track_id)
            self._update_track(detection, track_id, timestamp_s)

        for track_id in list(unmatched_tracks):
            track = self.tracks[track_id]
            track.missed += 1
            if track.missed > self.max_missed:
                del self.tracks[track_id]
                self.motion.discard(track_id)
        return detections

    def _match(
        self,
        detection: Detection,
        available: set[int],
        timestamp_s: float,
    ) -> int | None:
        best_id = None
        best_score = 0.0
        for track_id in available:
            track = self.tracks[track_id]
            if track.object_type != detection.object_type:
                continue
            if not self._motion_is_plausible(track, detection, timestamp_s):
                continue
            score = iou(track.bbox, detection.bbox)
            if score > best_score:
                best_id = track_id
                best_score = score
        return best_id if best_score >= self.iou_threshold else None

    def _motion_is_plausible(
        self,
        track: _Track,
        detection: Detection,
        timestamp_s: float,
    ) -> bool:
        if track.distance_m is None or detection.distance_m is None:
            return timestamp_s > track.timestamp_s
        elapsed_s = timestamp_s - track.timestamp_s
        if elapsed_s <= 0.0:
            return False
        distance_rate = abs(track.distance_m - detection.distance_m) / elapsed_s
        return distance_rate <= self.maximum_association_speed_mps

    def _update_track(
        self,
        detection: Detection,
        track_id: int,
        timestamp_s: float,
    ) -> None:
        detection.track_id = track_id
        previous = self.tracks.get(track_id)
        if previous is not None and (
            previous.distance_m is None or detection.distance_m is None
        ):
            self.motion.discard(track_id)
        if detection.distance_m is not None:
            motion = self.motion.update(
                track_id=track_id,
                timestamp_s=timestamp_s,
                distance_m=detection.distance_m,
            )
            detection.relative_speed_mps = motion.relative_speed_mps
            detection.ttc_s = motion.ttc_s
        self.tracks[track_id] = _Track(
            object_type=detection.object_type,
            bbox=detection.bbox,
            timestamp_s=timestamp_s,
            distance_m=detection.distance_m,
        )


def iou(
    box_a: tuple[float, float, float, float],
    box_b: tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    intersection_width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    intersection_height = max(0.0, min(ay2, by2) - max(ay1, by1))
    intersection = intersection_width * intersection_height
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection
    return 0.0 if union <= 0.0 else float(intersection / union)
