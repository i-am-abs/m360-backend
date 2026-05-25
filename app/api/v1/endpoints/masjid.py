from __future__ import annotations

import zlib
from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_user, get_settings
from app.api.v1.presenters.masjid_presenter import MasjidDetailsPresenter
from app.core.config import Settings
from app.core.enums.api_endpoints import ApiEndpoint
from app.core.enums.error_code import ErrorCode
from app.core.enums.masjid import MasjidQueryDefault
from app.exceptions.base import ApiException
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.modules.feature_flag.infrastructure.adapters.location_based_feature_flag_adapter import (
    LocationBasedFeatureFlagAdapter,
)
from app.services.user_masjid_service import UserMasjidService
from app.utils.response import success_response

router = APIRouter(tags=["masjids"])


class MasjidController:
    def __init__(
            self,
            masjidSearchService: MasjidSearchService,
            userMasjidService: UserMasjidService,
            userRepository: UserRepository,
            locationBasedFeatureFlagService: LocationBasedFeatureFlagAdapter,
            settings: Settings,
    ) -> None:
        self.masjidSearchService = masjidSearchService
        self.userMasjidService = userMasjidService
        self.userRepository = userRepository
        self.locationBasedFeatureFlagService = locationBasedFeatureFlagService
        self.settings = settings

    def searchNearby(
            self,
            latitude: float,
            longitude: float,
            radius: int,
            maxResultCount: int,
    ) -> Dict[str, Any]:
        if not self.locationBasedFeatureFlagService.isFeatureEnabledAtLocation(
            "MASJID_SEARCH_FEATURE", latitude, longitude
        ):
            raise ApiException(
                "Masjid search feature is not enabled at your current geographic location.",
                status_code=HTTPStatus.FORBIDDEN.value,
                code=ErrorCode.LOCATION_OUT_OF_BOUNDS
            )
        return self.masjidSearchService.search_nearby(latitude, longitude, radius, maxResultCount)

    def searchByName(
            self,
            query: str,
            limit: int,
            radius: Optional[int],
    ) -> Dict[str, Any]:
        return self.masjidSearchService.search_by_name(query, limit, radius)

    def searchByCity(
            self,
            city: str,
            maxResultCount: int,
            radiusMeters: int,
    ) -> Dict[str, Any]:
        return self.masjidSearchService.search_by_city(city, maxResultCount, radiusMeters)

    def getPlaceById(self, placeId: str) -> Dict[str, Any]:
        return self.masjidSearchService.get_place_by_id(placeId)

    def getMasjidDetails(self, placeId: str, currentUserId: str) -> Dict[str, Any]:
        place = self.masjidSearchService.get_place_by_id(placeId)
        pid = place.get("id") or placeId
        
        loc = place.get("location") or {}
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        
        if lat is not None and lng is not None:
            hasDonations = self.locationBasedFeatureFlagService.isFeatureEnabledAtLocation(
                "DONATIONS_FEATURE", float(lat), float(lng)
            )
            hasAnnouncements = self.locationBasedFeatureFlagService.isFeatureEnabledAtLocation(
                "ANNOUNCEMENTS_FEATURE", float(lat), float(lng)
            )
        else:
            hasDonations = False
            hasAnnouncements = False
            
        h = zlib.crc32((pid or "").encode("utf-8"))
        donationCount = (h % 5) if hasDonations else 0
        announcementCount = (h % 7) if hasAnnouncements else 0
        
        favorites = self.userRepository.listFavorites(currentUserId)
        isAdded = pid in favorites
        savedCount = len(favorites)
        
        return MasjidDetailsPresenter.toView(
            place=place,
            hasDonations=hasDonations,
            hasAnnouncements=hasAnnouncements,
            donationCount=donationCount,
            announcementCount=announcementCount,
            isAdded=isAdded,
            savedCount=savedCount,
        )

    def listMyMasjids(self, currentUserId: str) -> Dict[str, Any]:
        return self.userMasjidService.listMyMasjids(currentUserId)

    def addMyMasjid(self, currentUserId: str, placeId: str) -> Dict[str, Any]:
        return self.userMasjidService.addMyMasjid(currentUserId, placeId)

    def removeMyMasjid(self, currentUserId: str, placeId: str) -> Dict[str, Any]:
        return self.userMasjidService.removeMyMasjid(currentUserId, placeId)


def get_masjid_controller(request: Request) -> MasjidController:
    return MasjidController(
        masjidSearchService=request.app.state.masjid_search_service,
        userMasjidService=request.app.state.user_masjid_service,
        userRepository=request.app.state.user_store,
        locationBasedFeatureFlagService=request.app.state.location_based_feature_flag_service,
        settings=request.app.state.settings,
    )


@router.get(ApiEndpoint.MASJID_NEARBY.value, summary="Search nearby masjids")
def get_masjid_nearby(
        latitude: float,
        longitude: float,
        radius: int = MasjidQueryDefault.NEARBY_RADIUS_M.value,
        max_result_count: int = MasjidQueryDefault.NEARBY_MAX_RESULTS.value,
        controller: MasjidController = Depends(get_masjid_controller),
):
    return success_response(controller.searchNearby(latitude, longitude, radius, max_result_count))


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
        controller: MasjidController = Depends(get_masjid_controller),
        settings: Settings = Depends(get_settings),
):
    limit = maxResultCount if maxResultCount is not None else max_result_count
    radius = radius_meters if radius_meters is not None else radiusMeters
    if radius is None:
        radius = settings.masjid_search_radius_meters
    return success_response(controller.searchByName(q, limit, radius))


@router.get(ApiEndpoint.MASJID_BY_CITY.value, summary="Search masjids by city")
def get_masjid_by_city(
        city: str,
        max_result_count: int = MasjidQueryDefault.BY_CITY_MAX_RESULTS.value,
        radius_meters: Optional[int] = Query(
            None,
            ge=MasjidQueryDefault.SEARCH_RADIUS_MIN_M.value,
            le=MasjidQueryDefault.SEARCH_RADIUS_MAX_M.value,
        ),
        controller: MasjidController = Depends(get_masjid_controller),
        settings: Settings = Depends(get_settings),
):
    if radius_meters is None:
        radius_meters = settings.masjid_search_radius_meters
    return success_response(controller.searchByCity(city, max_result_count, radius_meters))


@router.get(ApiEndpoint.MASJID_PLACE.value, summary="Get place by ID")
def get_masjid_place(
        place_id: str = Query(..., description="Google Place ID"),
        controller: MasjidController = Depends(get_masjid_controller),
):
    return success_response(controller.getPlaceById(place_id))


@router.get(ApiEndpoint.MASJID_STATUS.value, summary="Masjid module status")
def get_masjid_status(settings: Settings = Depends(get_settings)):
    return success_response({"enabled": settings.masjid_module_active})


@router.get(ApiEndpoint.MASJID_DETAILS.value, summary="Get masjid full details")
def get_masjid_details(
        place_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        controller: MasjidController = Depends(get_masjid_controller),
):
    return success_response(controller.getMasjidDetails(place_id, current_user["user_id"]))


@router.get(ApiEndpoint.MY_MASJIDS.value, summary="List my favourite masjids")
def list_my_masjids(
        current_user: Dict[str, Any] = Depends(get_current_user),
        controller: MasjidController = Depends(get_masjid_controller),
):
    return success_response(controller.listMyMasjids(current_user["user_id"]))


@router.post(ApiEndpoint.MY_MASJID_ADD.value, summary="Add masjid to favourites")
def add_my_masjid(
        place_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        controller: MasjidController = Depends(get_masjid_controller),
):
    return success_response(controller.addMyMasjid(current_user["user_id"], place_id), message="Masjid added")


@router.delete(ApiEndpoint.MY_MASJID_REMOVE.value, summary="Remove from favourites")
def remove_my_masjid(
        place_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        controller: MasjidController = Depends(get_masjid_controller),
):
    return success_response(controller.removeMyMasjid(current_user["user_id"], place_id), message="Masjid removed")
