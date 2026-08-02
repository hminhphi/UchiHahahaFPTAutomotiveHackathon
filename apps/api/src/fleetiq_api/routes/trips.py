"""Trip queries and immutable historical evidence-frame access."""

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..dependencies import AppDependencies
from ..schemas import TrajectoryEnvelope, TripListData, TripListEnvelope, utc_now

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_VIEWS = frozenset({"road_left", "road_right", "driver"})


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
