"""Minimal typed trip query routes."""

from fastapi import APIRouter, Request

from ..dependencies import AppDependencies
from ..schemas import TripListData, TripListEnvelope, utc_now

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])


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
