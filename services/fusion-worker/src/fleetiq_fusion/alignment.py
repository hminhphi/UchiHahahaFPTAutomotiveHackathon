"""Frame-level alignment checks for fused signals."""

from typing import Protocol


class FrameSignal(Protocol):
    trip_id: str
    frame_index: int
    correlation_id: str


class SignalAligner:
    def __init__(self, *, frame_tolerance: int = 1) -> None:
        if frame_tolerance < 0:
            raise ValueError("frame tolerance cannot be negative")
        self.frame_tolerance = frame_tolerance

    def validate(self, *signals: FrameSignal) -> None:
        if not signals:
            raise ValueError("at least one signal is required")
        trips = {signal.trip_id for signal in signals}
        if len(trips) != 1:
            raise ValueError("fusion signals must belong to the same trip")
        correlations = {signal.correlation_id for signal in signals}
        if len(correlations) != 1:
            raise ValueError("fusion signals must share one correlation ID")
        frames = [signal.frame_index for signal in signals]
        if max(frames) - min(frames) > self.frame_tolerance:
            raise ValueError("fusion signals exceed the frame alignment tolerance")
