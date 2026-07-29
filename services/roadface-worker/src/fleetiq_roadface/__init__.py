"""FleetIQ road-facing inference runtime."""

from typing import TYPE_CHECKING, Any

from .types import Detection, LaneEstimate, RoadFrameResult, TrackedObstacle

if TYPE_CHECKING:
    from .pipeline import PipelineOptions, RoadfacePipeline

__all__ = [
    "Detection",
    "LaneEstimate",
    "PipelineOptions",
    "RoadFrameResult",
    "RoadfacePipeline",
    "TrackedObstacle",
]

_LAZY_PIPELINE_EXPORTS = {"PipelineOptions", "RoadfacePipeline"}


def __getattr__(name: str) -> Any:
    """Load OpenCV-backed runtime exports only when callers request them."""
    if name not in _LAZY_PIPELINE_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from .pipeline import PipelineOptions, RoadfacePipeline

    exports = {
        "PipelineOptions": PipelineOptions,
        "RoadfacePipeline": RoadfacePipeline,
    }
    globals().update(exports)
    return exports[name]


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
