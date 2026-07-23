from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_admin_store,
    get_current_user,
    get_masjid_search_service,
    get_masjid_store,
    get_settings,
    get_user_masjid_service,
    get_user_store,
)
from app.api.v1.presenters.masjid_presenter import MasjidDetailsPresenter
from app.core.config import Settings
from app.core.enums.api_endpoints import ApiEndpoint
from app.core.enums.masjid import MasjidQueryDefault
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.services.user_masjid_service import UserMasjidService
from app.utils.admin_link import resolve_committee_for_place
from app.utils.masjid import get_deterministic_masjid_metadata
from app.utils.response import success_response

router = APIRouter(tags=["masjids"])


@router.get(ApiEndpoint.MASJID_NEARBY.value, summary="Search nearby masjids")
def get_masjid_nearby(
        latitude: float,
        longitude: float,
        radius: int = MasjidQueryDefault.NEARBY_RADIUS_M.value,
        max_result_count: int = MasjidQueryDefault.NEARBY_MAX_RESULTS.value,
        svc: MasjidSearchService = Depends(get_masjid_search_service),
):
    return success_response(svc.search_nearby(latitude, longitude, radius, max_result_count))


@router.get(ApiEndpoint.MASJID_SEARCH.value, summary="Search masjid by name")
@router.get(ApiEndpoint.MASJID_SEARCH_SHORT.value, summary="Search masjid (short)")
def search_masjid_by_name(
        q: str,
        max_result_count: int = MasjidQueryDefault.TEXT_SEARCH_MAX_RESULTS.value,
        maxResultCount: Optional[int] = Query(None, ge=1),
        radius_meters: Optional[int] = Query(
            None,
            ge=MasjidQueryDefault.SEARCH_RADIUS_MIN_M.value,
            le=MasjidQueryDefault.SEARCH_RADIUS_MAX_M.value,
        ),
        radiusMeters: Optional[int] = Query(
            None,
            ge=MasjidQueryDefault.SEARCH_RADIUS_MIN_M.value,
            le=MasjidQueryDefault.SEARCH_RADIUS_MAX_M.value,
        ),
        svc: MasjidSearchService = Depends(get_masjid_search_service),
        settings: Settings = Depends(get_settings),
):
    limit = maxResultCount if maxResultCount is not None else max_result_count
    radius = radius_meters if radius_meters is not None else radiusMeters
    if radius is None:
        radius = settings.masjid_search_radius_meters
    return success_response(svc.search_by_name(q, limit, radius))


@router.get(ApiEndpoint.MASJID_BY_CITY.value, summary="Search masjids by city")
def get_masjid_by_city(
        city: str,
        max_result_count: int = MasjidQueryDefault.BY_CITY_MAX_RESULTS.value,
        radius_meters: Optional[int] = Query(
            None,
            ge=MasjidQueryDefault.SEARCH_RADIUS_MIN_M.value,
            le=MasjidQueryDefault.SEARCH_RADIUS_MAX_M.value,
        ),
        svc: MasjidSearchService = Depends(get_masjid_search_service),
        settings: Settings = Depends(get_settings),
):
    if radius_meters is None:
        radius_meters = settings.masjid_search_radius_meters
    return success_response(svc.search_by_city(city, max_result_count, radius_meters))


@router.get(ApiEndpoint.MASJID_PLACE.value, summary="Get place by ID")
def get_masjid_place(
        place_id: str = Query(..., description="Google Place ID"),
        svc: MasjidSearchService = Depends(get_masjid_search_service),
):
    return success_response(svc.get_place_by_id(place_id))


@router.get(ApiEndpoint.MASJID_STATUS.value, summary="Masjid module status")
def get_masjid_status(settings: Settings = Depends(get_settings)):
    return success_response({"enabled": settings.masjid_module_enabled})


@router.get(ApiEndpoint.MASJID_DETAILS.value, summary="Get masjid full details")
def get_masjid_details(
        place_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        store: UserRepository = Depends(get_user_store),
        svc: MasjidSearchService = Depends(get_masjid_search_service),
        masjid_store: MasjidRepository = Depends(get_masjid_store),
        admin_store: AdminRepository = Depends(get_admin_store),
):
    place = svc.get_place_by_id(place_id)
    pid = place.get("id") or place_id
    meta = get_deterministic_masjid_metadata(pid)
    favorites = store.list_favorites(current_user["phone_number"])
    is_added = pid in favorites
    saved_count = len(favorites)

    committee = resolve_committee_for_place(
        pid,
        admin_store=admin_store,
        masjid_store=masjid_store,
    )
    prayer_timings = masjid_store.get_timings(pid) or []
    amenities = masjid_store.get_amenities(pid) or []
    view = MasjidDetailsPresenter.to_view(
        place,
        has_donations=meta["hasDonationsEnabled"],
        has_announcements=meta["hasAnnouncementsEnabled"],
        donation_count=meta["donationUpdatesCount"],
        announcement_count=meta["announcementUpdatesCount"],
        is_added=is_added,
        saved_count=saved_count,
        committee_data=committee["details"] if committee["has_committee"] else None,
        prayer_timings=prayer_timings,
        amenities=amenities,
    )
    view["committee"] = committee
    return success_response(view)


@router.get(ApiEndpoint.MY_MASJIDS.value, summary="List my favourite masjids")
def list_my_masjids(current_user: Dict[str, Any] = Depends(get_current_user),
                    svc: UserMasjidService = Depends(get_user_masjid_service), ):
    return success_response(svc.list_my_masjids(current_user))


@router.post(ApiEndpoint.MY_MASJID_ADD.value, summary="Add masjid to favourites")
def add_my_masjid(place_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
                  svc: UserMasjidService = Depends(get_user_masjid_service), ):
    return success_response(svc.add_my_masjid(current_user, place_id), message="Masjid added")


@router.delete(ApiEndpoint.MY_MASJID_REMOVE.value, summary="Remove from favourites")
def remove_my_masjid(place_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
                     svc: UserMasjidService = Depends(get_user_masjid_service), ):
    return success_response(svc.remove_my_masjid(current_user, place_id), message="Masjid removed")
