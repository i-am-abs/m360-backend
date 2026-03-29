from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_masjid_places_service
from constants.api_endpoints import ApiEndpoints
from constants.masjid_query import MasjidQueryLimits
from exceptions.api_exception import ApiException
from services.google_places.contracts import MasjidPlacesService
from services.google_places.support.env import (
    get_masjid_search_default_radius_meters,
    is_masjid_module_enabled,
)
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
