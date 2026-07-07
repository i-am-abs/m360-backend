from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_masjid_entity_service, get_masjid_search_service, \
    get_optional_current_user, get_settings, get_user_masjid_service, get_user_store
from app.api.v1.presenters.masjid_presenter import MasjidDetailsPresenter
from app.core.config import Settings
from app.core.enums.api_endpoints import ApiEndpoint
from app.core.enums.masjid import MasjidQueryDefault
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.schemas.masjid_entity import CommitteeMemberAdd, MasjidSyncRequest, MasjidUpdate, TimingsUpdate
from app.services.masjid_entity_service import MasjidEntityService
from app.services.user_masjid_service import UserMasjidService
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
def get_masjid_details(place_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
                       store: UserRepository = Depends(get_user_store),
                       svc: MasjidSearchService = Depends(get_masjid_search_service), ):
    place = svc.get_place_by_id(place_id)
    pid = place.get("id") or place_id
    meta = get_deterministic_masjid_metadata(pid)
    user_id = current_user["user_id"]
    favorites = store.list_favorites(user_id)
    is_added = pid in favorites
    saved_count = len(favorites)
    return success_response(
        MasjidDetailsPresenter.to_view(
            place,
            has_donations=meta["hasDonationsEnabled"],
            has_announcements=meta["hasAnnouncementsEnabled"],
            donation_count=meta["donationUpdatesCount"],
            announcement_count=meta["announcementUpdatesCount"],
            is_added=is_added,
            saved_count=saved_count,
        )
    )


@router.get(ApiEndpoint.MY_MASJIDS.value, summary="List my favourite masjids")
def list_my_masjids(current_user: Dict[str, Any] = Depends(get_current_user),
                    svc: UserMasjidService = Depends(get_user_masjid_service), ):
    return success_response(svc.list_my_masjids(current_user["user_id"]))


@router.get(ApiEndpoint.MASJID_LIST.value + "/my-committee", summary="List masjids where I'm committee")
def list_my_committee_masjids(
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    return success_response(svc.list_committee_masjids(current_user["user_id"]))


@router.post(ApiEndpoint.MY_MASJID_ADD.value, summary="Add masjid to favourites")
def add_my_masjid(place_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
                  svc: UserMasjidService = Depends(get_user_masjid_service), ):
    return success_response(svc.add_my_masjid(current_user["user_id"], place_id), message="Masjid added")


@router.delete(ApiEndpoint.MY_MASJID_REMOVE.value, summary="Remove from favourites")
def remove_my_masjid(place_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
                     svc: UserMasjidService = Depends(get_user_masjid_service), ):
    return success_response(svc.remove_my_masjid(current_user["user_id"], place_id), message="Masjid removed")


@router.get(ApiEndpoint.MASJID_LIST.value, summary="List masjids from DB")
def list_masjids(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius: int = Query(5000),
    city: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    if lat is not None and lng is not None:
        return success_response(svc.search_nearby(lat, lng, radius, limit, page))
    if city:
        return success_response(svc.search_by_name(city, limit, page))
    return success_response(svc.get_masjid_list(page, limit))


@router.get(ApiEndpoint.MASJID_GET.value, summary="Get masjid detail")
def get_masjid(
    masjid_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    user_id = current_user["user_id"] if current_user else None
    return success_response(svc.get_masjid(masjid_id, user_id=user_id))


@router.post(ApiEndpoint.MASJID_SYNC.value, summary="Sync Google Place into DB")
def sync_masjid(
    req: MasjidSyncRequest,
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    return success_response(svc.sync_place_id(req.place_id))


@router.put(ApiEndpoint.MASJID_UPDATE.value, summary="Update masjid")
def update_masjid(
    masjid_id: str,
    updates: MasjidUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    return success_response(
        svc.update_masjid(masjid_id, updates.model_dump(exclude_none=True), current_user["user_id"])
    )


@router.put(ApiEndpoint.MASJID_UPDATE_FACILITIES.value, summary="Update facilities")
def update_facilities(
    masjid_id: str,
    facilities: Dict[str, bool],
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    return success_response(
        svc.update_facilities(masjid_id, facilities, current_user["user_id"])
    )


@router.put(ApiEndpoint.MASJID_UPDATE_TIMINGS.value, summary="Update timings")
def update_timings(
    masjid_id: str,
    timings: TimingsUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    return success_response(
        svc.update_timings(masjid_id, timings.model_dump(exclude_none=True), current_user["user_id"])
    )


@router.post(ApiEndpoint.MASJID_COMMITTEE_ADD.value, summary="Add committee member")
def add_committee_member(
    masjid_id: str,
    member: CommitteeMemberAdd,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    return success_response(svc.add_committee_member(masjid_id, member.model_dump()))


@router.delete(ApiEndpoint.MASJID_COMMITTEE_REMOVE.value, summary="Remove committee member")
def remove_committee_member(
    masjid_id: str,
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    return success_response(svc.remove_committee_member(masjid_id, user_id, current_user["user_id"]))
