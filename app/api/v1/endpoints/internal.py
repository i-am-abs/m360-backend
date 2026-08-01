from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_broadcast_service,
    get_internal_timings_service,
    verify_internal_api_key,
)
from app.core.enums.api_endpoints import ApiEndpoint
from app.services.broadcast_service import BroadcastService
from app.services.internal_timings_service import InternalTimingsService
from app.utils.response import success_response

router = APIRouter(tags=["internal"])


@router.get(
    ApiEndpoint.INTERNAL_MASJID_TIMINGS.value,
    summary="Internal masjid timings (cached, high-frequency)",
    dependencies=[Depends(verify_internal_api_key)],
)
def get_internal_masjid_timings(
        place_id: str,
        svc: InternalTimingsService = Depends(get_internal_timings_service),
):
    result = svc.get_timings(place_id)
    return success_response(result.model_dump(by_alias=True))


@router.post(
    ApiEndpoint.INTERNAL_MASJID_BROADCAST.value,
    summary="Internal: re-send broadcast to all masjid followers",
    dependencies=[Depends(verify_internal_api_key)],
)
def internal_broadcast_to_followers(
        place_id: str,
        broadcast_id: str = Query(..., description="Existing broadcast id to fan out"),
        svc: BroadcastService = Depends(get_broadcast_service),
):
    result = svc.notify_followers_internal(place_id, broadcast_id)
    return success_response(result.model_dump(by_alias=True), message="Broadcast dispatched")
