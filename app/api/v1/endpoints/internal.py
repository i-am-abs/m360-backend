from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_internal_timings_service, verify_internal_api_key
from app.core.enums.api_endpoints import ApiEndpoint
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
