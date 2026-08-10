"""Trip queries and immutable historical evidence-frame access."""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from ..dependencies import AppDependencies
from ..schemas import TrajectoryEnvelope, TripListData, TripListEnvelope, utc_now

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_VIEWS = frozenset({"road_left", "road_right", "driver"})
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
        request.app.state.settings.model_extra.get("artifacts_root", "")
        or __import__("os").environ.get("FLEETIQ_ARTIFACTS_ROOT", "artifacts/trips")
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
