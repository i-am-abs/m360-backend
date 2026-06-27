from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_current_user,
    get_masjid_amenities_service,
    get_masjid_listing_service,
    get_masjid_timings_service,
)
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.masjid_content import MasjidAmenitiesRequest, MasjidTimingsRequest
from app.services.masjid_amenities_service import MasjidAmenitiesService
from app.services.masjid_listing_service import MasjidListingService
from app.services.masjid_timings_service import MasjidTimingsService
from app.utils.response import success_response

router = APIRouter(tags=["masjids"])


@router.get(ApiEndpoint.MASJIDS_LIST.value, summary="List user masjids with admin status")
def list_masjids(
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: MasjidListingService = Depends(get_masjid_listing_service),
):
    items = svc.list_masjids_for_user(current_user)
    return success_response([item.model_dump(by_alias=True) for item in items])


@router.post(ApiEndpoint.MASJID_TIMINGS.value, summary="Create masjid prayer timings")
def create_masjid_timings(
        place_id: str,
        body: MasjidTimingsRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: MasjidTimingsService = Depends(get_masjid_timings_service),
):
    result = svc.create_timings(place_id, body, current_user)
    return success_response(result, message="Timings saved")


@router.put(ApiEndpoint.MASJID_TIMINGS.value, summary="Update masjid prayer timings")
def update_masjid_timings(
        place_id: str,
        body: MasjidTimingsRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: MasjidTimingsService = Depends(get_masjid_timings_service),
):
    result = svc.update_timings(place_id, body, current_user)
    return success_response(result, message="Timings updated")


@router.post(ApiEndpoint.MASJID_AMENITIES.value, summary="Create masjid amenities")
def create_masjid_amenities(
        place_id: str,
        body: MasjidAmenitiesRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: MasjidAmenitiesService = Depends(get_masjid_amenities_service),
):
    result = svc.create_amenities(place_id, body, current_user)
    return success_response(result, message="Amenities saved")


@router.put(ApiEndpoint.MASJID_AMENITIES.value, summary="Update masjid amenities")
def update_masjid_amenities(
        place_id: str,
        body: MasjidAmenitiesRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: MasjidAmenitiesService = Depends(get_masjid_amenities_service),
):
    result = svc.update_amenities(place_id, body, current_user)
    return success_response(result, message="Amenities updated")
