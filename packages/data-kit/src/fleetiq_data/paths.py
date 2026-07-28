"""Explicit dataset-root configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatasetPaths:
    """The directory that directly contains organizer trip folders."""

    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).expanduser())

    @classmethod
    def from_env(cls) -> DatasetPaths:
        """Build paths from the one supported environment variable."""
        value = os.environ.get("FLEETIQ_DATA_ROOT")
        if not value:
            raise ValueError("FLEETIQ_DATA_ROOT is not set")
        return cls(Path(value))
