from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import (
    get_current_user,
    get_masjid_places_service,
    get_user_masjid_service,
)
from constants.api_endpoints import ApiEndpoints
from constants.masjid_query import MasjidQueryLimits
from exceptions.api_exception import ApiException
from services.google_places.contracts import MasjidPlacesService
from services.google_places.support.env import (
    get_masjid_search_default_radius_meters,
    is_masjid_module_enabled,
)
from services.user_masjid_service import UserMasjidService
from utils.http_response import success_response

masjid_router = APIRouter(tags=["masjids"])


def _masjid_search_by_name_response(
    q: str,
    max_result_count: int,
    radius_meters: Optional[int],
    svc: MasjidPlacesService,
):
    if radius_meters is None:
        radius_meters = get_masjid_search_default_radius_meters()
    data = svc.search_masjid_by_name(
        query=q,
        max_result_count=max_result_count,
        radius_meters=radius_meters,
    )
    return success_response(data)


@masjid_router.get(ApiEndpoints.MASJID_NEARBY.value)
def get_masjid_nearby(
    latitude: float,
    longitude: float,
    radius: int = MasjidQueryLimits.NEARBY_RADIUS_DEFAULT_M,
    max_result_count: int = MasjidQueryLimits.NEARBY_MAX_RESULTS_DEFAULT,
    svc: MasjidPlacesService = Depends(get_masjid_places_service),
):
    try:
        data = svc.search_nearby_masjid(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius,
            max_result_count=max_result_count,
        )
        return success_response(data)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            detail=str(e),
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_SEARCH.value)
@masjid_router.get(ApiEndpoints.MASJID_SEARCH_SHORT.value)
def search_masjid_by_name(
    q: str,
    max_result_count: int = MasjidQueryLimits.TEXT_SEARCH_MAX_RESULTS_DEFAULT,
    maxResultCount: Optional[int] = Query(
        None,
        ge=1,
        description="CamelCase alias for max_result_count (wins when set).",
    ),
    radius_meters: Optional[int] = Query(
        None,
        ge=MasjidQueryLimits.SEARCH_RADIUS_MIN_M,
        le=MasjidQueryLimits.SEARCH_RADIUS_MAX_M,
        description=(
            "Radius in meters around the geocoded location (India). "
            "Default from MASJID_SEARCH_RADIUS_METERS env or 5000."
        ),
    ),
    radiusMeters: Optional[int] = Query(
        None,
        ge=MasjidQueryLimits.SEARCH_RADIUS_MIN_M,
        le=MasjidQueryLimits.SEARCH_RADIUS_MAX_M,
        description="CamelCase alias for radius_meters.",
    ),
    svc: MasjidPlacesService = Depends(get_masjid_places_service),
):
    try:
        limit = (
            maxResultCount if maxResultCount is not None else max_result_count
        )
        radius = radius_meters if radius_meters is not None else radiusMeters
        return _masjid_search_by_name_response(q, limit, radius, svc)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            detail=str(e),
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_BY_CITY.value)
def get_masjid_by_city(
    city: str,
    max_result_count: int = MasjidQueryLimits.BY_CITY_MAX_RESULTS_DEFAULT,
    radius_meters: Optional[int] = Query(
        None,
        ge=MasjidQueryLimits.SEARCH_RADIUS_MIN_M,
        le=MasjidQueryLimits.SEARCH_RADIUS_MAX_M,
        description=(
            "Radius in meters around the geocoded city/area (India). "
            "Default from MASJID_SEARCH_RADIUS_METERS env or 5000."
        ),
    ),
    svc: MasjidPlacesService = Depends(get_masjid_places_service),
):
    try:
        if radius_meters is None:
            radius_meters = get_masjid_search_default_radius_meters()
        data = svc.search_masjid_by_city(
            city=city,
            max_result_count=max_result_count,
            radius_meters=radius_meters,
        )
        return success_response(data)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            detail=str(e),
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_PLACE.value)
def get_masjid_place(
    place_id: str = Query(..., description="Google Place ID"),
    svc: MasjidPlacesService = Depends(get_masjid_places_service),
):
    try:
        data = svc.get_place_by_id(place_id)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST.value,
            detail=str(e),
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_STATUS.value)
def get_masjid_status():
    return success_response({"enabled": is_masjid_module_enabled()})


def _extract_masjid_details(place: Dict[str, Any]) -> Dict[str, Any]:
    accessibility = place.get("accessibilityOptions") or {}
    amenity = place.get("amenityOptions") or {}
    payment = place.get("paymentOptions") or {}
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "address": place.get("formattedAddress"),
        "location": place.get("location"),
        "timings": {
            "current_opening_hours": place.get("currentOpeningHours"),
            "regular_opening_hours": place.get("regularOpeningHours"),
        },
        "management": {
            "phone_number": place.get("internationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "business_status": place.get("businessStatus"),
        },
        "facilities": {
            "wheelchair_accessible_entrance": accessibility.get(
                "wheelchairAccessibleEntrance"
            ),
            "wheelchair_accessible_parking": accessibility.get(
                "wheelchairAccessibleParking"
            ),
            "restroom": amenity.get("restroom"),
            "free_parking_lot": amenity.get("freeParkingLot"),
            "accepts_nfc": payment.get("acceptsNfc"),
        },
        "raw": place,
    }


@masjid_router.get(ApiEndpoints.MASJID_DETAILS.value)
def get_masjid_details(
    place_id: str,
    svc: MasjidPlacesService = Depends(get_masjid_places_service),
):
    try:
        place = svc.get_place_by_id(place_id)
        return success_response(_extract_masjid_details(place))
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST.value,
            detail=str(e),
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MY_MASJIDS.value)
def list_my_masjids(
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: UserMasjidService = Depends(get_user_masjid_service),
):
    data = svc.list_my_masjids(current_user["user_id"])
    return success_response(data)


@masjid_router.post(ApiEndpoints.MY_MASJID_ADD.value)
def add_my_masjid(
    place_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: UserMasjidService = Depends(get_user_masjid_service),
):
    data = svc.add_my_masjid(current_user["user_id"], place_id)
    return success_response(data, message="Masjid added to favorites")


@masjid_router.delete(ApiEndpoints.MY_MASJID_REMOVE.value)
def remove_my_masjid(
    place_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: UserMasjidService = Depends(get_user_masjid_service),
):
    data = svc.remove_my_masjid(current_user["user_id"], place_id)
    return success_response(data, message="Masjid removed from favorites")
