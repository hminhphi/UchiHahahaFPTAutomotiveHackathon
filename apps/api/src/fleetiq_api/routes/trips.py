"""Trip queries and immutable historical evidence-frame access."""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from ..dependencies import AppDependencies
from ..operations import RoadVideoDescriptor, VideoFrameMapEntry
from ..schemas import TrajectoryEnvelope, TripListData, TripListEnvelope, utc_now

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_VIEWS = frozenset({"road_left", "road_right", "driver", "depth"})
_ANALYSIS_KINDS = frozenset({"road", "dms", "fusion"})


@router.get("", response_model=TripListEnvelope)
async def list_trips(request: Request) -> TripListEnvelope:
    dependencies: AppDependencies = request.app.state.dependencies
    items = await dependencies.trips.list_trips()
    return TripListEnvelope(
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        timestamp=utc_now(),
        data=TripListData(items=items),
    )


@router.get("/{trip_id}/trajectory", response_model=TrajectoryEnvelope)
async def get_trajectory(request: Request, trip_id: str) -> TrajectoryEnvelope:
    dependencies = request.app.state.dependencies
    trajectory = await dependencies.trajectory.get_trajectory(trip_id)
    return TrajectoryEnvelope(
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        timestamp=utc_now(),
        data=trajectory,
    )


@router.get("/{trip_id}/frames/{view}/{frame_index}", response_class=Response)
async def get_historical_frame(
    request: Request,
    trip_id: str,
    view: str,
    frame_index: int,
) -> Response:
    """Serve one evidence image so a historical trip can be scrubbed precisely."""
    if not _SAFE_IDENTIFIER.fullmatch(trip_id) or view not in _VIEWS or frame_index < 0:
        raise HTTPException(status_code=404, detail="Historical frame not found")
    if view == "depth":
        return _depth_frame(trip_id, frame_index)
    reader = request.app.state.dependencies.frame_reader
    if reader is None:
        raise HTTPException(status_code=404, detail="Historical frame replay is disabled")
    try:
        frame = await reader.get_frame(trip_id, view, frame_index)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Historical frame not found") from None
    return Response(
        content=frame.jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, max-age=300",
            "X-FleetIQ-Frame-Index": str(frame.metadata.frame_index),
            "X-FleetIQ-Frame-Width": str(frame.metadata.width),
            "X-FleetIQ-Frame-Height": str(frame.metadata.height),
        },
    )


def _depth_frame(trip_id: str, frame_index: int) -> Response:
    depth_dir = Path(
        __import__("os").environ.get("FLEETIQ_ARTIFACTS_ROOT", "artifacts/trips")
    ) / trip_id / "media" / "depth"
    for candidate in range(frame_index, max(-1, frame_index - 10), -1):
        depth_path = depth_dir / f"{candidate:06d}.png"
        if depth_path.is_file():
            return Response(
                content=depth_path.read_bytes(),
                media_type="image/png",
                headers={
                    "Cache-Control": "private, max-age=300",
                    "X-FleetIQ-Frame-Index": str(candidate),
                },
            )
    raise HTTPException(status_code=404, detail="Historical frame not found")


@router.get("/{trip_id}/road-video")
async def get_road_video(trip_id: str) -> JSONResponse:
    if not _SAFE_IDENTIFIER.fullmatch(trip_id):
        raise HTTPException(status_code=404, detail="Road video unavailable")
    media_root = Path(
        __import__("os").environ.get("FLEETIQ_ARTIFACTS_ROOT", "artifacts/trips")
    ) / trip_id / "media" / "road_left"
    try:
        manifest = json.loads((media_root / "manifest.json").read_text(encoding="utf-8"))
        fps = float(manifest["fps"])
        frame_map = tuple(
            VideoFrameMapEntry(
                frame_index=int(entry["frame_index"]),
                time_s=float(entry["time_s"]),
            )
            for entry in manifest["entries"]
        )
        descriptor = RoadVideoDescriptor(
            trip_id=trip_id,
            asset_url=f"/api/trips/{trip_id}/road-video/content",
            fps=fps,
            duration_s=(frame_map[-1].time_s + 1 / fps) if frame_map else 0,
            frame_map=frame_map,
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=404, detail="Road video unavailable") from None
    return JSONResponse({"data": descriptor.model_dump(mode="json")})


@router.get("/{trip_id}/road-video/content", response_class=Response)
async def get_road_video_content(request: Request, trip_id: str) -> Response:
    if not _SAFE_IDENTIFIER.fullmatch(trip_id):
        raise HTTPException(status_code=404, detail="Road video unavailable")
    video_path = Path(
        __import__("os").environ.get("FLEETIQ_ARTIFACTS_ROOT", "artifacts/trips")
    ) / trip_id / "media" / "road_left" / "source.mp4"
    try:
        content = video_path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Road video unavailable") from None
    start, end = _byte_range(request.headers.get("range"), len(content))
    status_code = 206 if request.headers.get("range") else 200
    headers = {"Accept-Ranges": "bytes", "Content-Length": str(end - start + 1)}
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{len(content)}"
    return Response(
        content=content[start : end + 1],
        status_code=status_code,
        media_type="video/mp4",
        headers=headers,
    )


@router.get("/{trip_id}/analysis/{kind}/frames/{frame_index}")
async def get_analysis_frame(
    request: Request,
    trip_id: str,
    kind: str,
    frame_index: int,
) -> JSONResponse:
    """Serve pre-computed per-frame AI analysis (road detections, DMS state, fusion score).

    Files live at artifacts/trips/{trip_id}/analysis/{kind}/{frame_index:06d}.json.
    The artifacts root is read from FLEETIQ_ARTIFACTS_ROOT (defaults to artifacts/trips).
    """
    if not _SAFE_IDENTIFIER.fullmatch(trip_id) or kind not in _ANALYSIS_KINDS or frame_index < 0:
        raise HTTPException(status_code=404, detail="Frame analysis not found")

    artifacts_root = Path(
        __import__("os").environ.get("FLEETIQ_ARTIFACTS_ROOT", "artifacts/trips")
    )
    analysis_path = artifacts_root / trip_id / "analysis" / kind / f"{frame_index:06d}.json"

    if not analysis_path.is_file():
        raise HTTPException(status_code=404, detail="Frame analysis not found")

    try:
        content = json.loads(analysis_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Failed to read frame analysis") from exc

    return JSONResponse(
        content=content,
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.get("/{trip_id}/analysis/fusion/summary")
async def get_fusion_summary(request: Request, trip_id: str) -> JSONResponse:
    """Serve the pre-computed per-trip fusion summary."""
    if not _SAFE_IDENTIFIER.fullmatch(trip_id):
        raise HTTPException(status_code=404, detail="Trip not found")

    artifacts_root = Path(
        __import__("os").environ.get("FLEETIQ_ARTIFACTS_ROOT", "artifacts/trips")
    )
    summary_path = artifacts_root / trip_id / "analysis" / "fusion" / "summary.json"

    if not summary_path.is_file():
        raise HTTPException(status_code=404, detail="Fusion summary not found")

    try:
        content = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Failed to read fusion summary") from exc

    return JSONResponse(
        content=content,
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.get("/{trip_id}/analysis/road/masks/{frame_index}", response_class=Response)
async def get_road_mask(request: Request, trip_id: str, frame_index: int) -> Response:
    """Serve a precomputed YOLOP drivable-road mask for the road overlay."""
    if not _SAFE_IDENTIFIER.fullmatch(trip_id) or frame_index < 0:
        raise HTTPException(status_code=404, detail="Road mask not found")
    import os

    mask_root = Path(
        os.environ.get(
            "FLEETIQ_YOLOP_ARTIFACT_ROOT",
            "artifacts/training/roadface/yolop_panoptic",
        )
    )
    mask_path = mask_root / trip_id / "road_masks" / f"{frame_index:06d}.png"
    if not mask_path.is_file():
        raise HTTPException(status_code=404, detail="Road mask not found")
    return Response(
        content=mask_path.read_bytes(),
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=300"},
    )


def _byte_range(value: str | None, size: int) -> tuple[int, int]:
    if size <= 0:
        raise HTTPException(status_code=404, detail="Road video unavailable")
    if not value or not value.startswith("bytes="):
        return 0, size - 1
    try:
        left, right = value[6:].split("-", 1)
        start = int(left) if left else 0
        end = int(right) if right else size - 1
    except ValueError:
        raise HTTPException(status_code=416, detail="Invalid video range") from None
    if start < 0 or start >= size or end < start:
        raise HTTPException(status_code=416, detail="Invalid video range")
    return start, min(end, size - 1)
