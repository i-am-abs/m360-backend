from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_current_user,
    get_masjid_amenities_service,
    get_masjid_announcements_service,
    get_masjid_entity_service,
    get_masjid_listing_service,
    get_masjid_timings_service,
    get_optional_current_user,
)
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.masjid_content import (
    MasjidAmenitiesRequest,
    MasjidAnnouncementsEnabledRequest,
    MasjidTimingsRequest,
)
from app.services.masjid_amenities_service import MasjidAmenitiesService
from app.services.masjid_announcements_service import MasjidAnnouncementsService
from app.services.masjid_entity_service import MasjidEntityService
from app.services.masjid_listing_service import MasjidListingService
from app.services.masjid_timings_service import MasjidTimingsService
from app.utils.response import success_response

router = APIRouter(tags=["masjids"])


@router.get(ApiEndpoint.MASJIDS_LIST.value, summary="List masjids")
def list_masjids(
        lat: Optional[float] = Query(None),
        lng: Optional[float] = Query(None),
        radius: int = Query(5000),
        city: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=50),
        current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
        svc_listing: MasjidListingService = Depends(get_masjid_listing_service),
        svc_entity: MasjidEntityService = Depends(get_masjid_entity_service),
):
    if lat is not None and lng is not None:
        return success_response(svc_entity.search_nearby(lat, lng, radius, limit, page))
    if city:
        return success_response(svc_entity.search_by_name(city, limit, page))
    if current_user is not None:
        items = svc_listing.list_masjids_for_user(current_user)
        return success_response(items)
    return success_response(svc_entity.get_masjid_list(page, limit))


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


@router.put(
    ApiEndpoint.MASJID_ANNOUNCEMENTS_ENABLED.value,
    summary="Enable or disable announcements for a masjid",
)
def set_masjid_announcements_enabled(
        place_id: str,
        body: MasjidAnnouncementsEnabledRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: MasjidAnnouncementsService = Depends(get_masjid_announcements_service),
):
    result = svc.set_announcements_enabled(place_id, body, current_user)
    return success_response(result, message="Announcements setting updated")
