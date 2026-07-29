"""Deterministic temporal smoothing for driver attention states."""

from collections import Counter, deque
from typing import Literal

DriverStateName = Literal["attentive", "distracted", "drowsy", "unknown"]
_STATES = frozenset(("attentive", "distracted", "drowsy", "unknown"))


class StateSmoother:
    def __init__(self, *, window_size: int = 5, min_votes: int = 3) -> None:
        if window_size < 1:
            raise ValueError("window_size must be positive")
        if min_votes < 1 or min_votes > window_size:
            raise ValueError("min_votes must be between one and window_size")
        self._window: deque[DriverStateName] = deque(maxlen=window_size)
        self._min_votes = min_votes
        self._current: DriverStateName = "unknown"

    @property
    def current(self) -> DriverStateName:
        return self._current

    def update(self, state: DriverStateName) -> DriverStateName:
        if state not in _STATES:
            raise ValueError("unsupported driver state")
        self._window.append(state)
        counts = Counter(self._window)
        highest = max(counts.values())
        candidates = {name for name, count in counts.items() if count == highest}
        if highest < self._min_votes:
            return self._current
        if self._current in candidates:
            return self._current
        if len(candidates) == 1:
            self._current = candidates.pop()
        return self._current
