from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from client.google_places_client import GooglePlacesClient, get_places_client
from constants.api_endpoints import ApiEndpoints
from exceptions.api_exception import ApiException
from utils.google_places import is_masjid_module_enabled
from utils.google_places.env import get_masjid_search_default_radius_meters
from utils.http_response import success_response

masjid_router = APIRouter(tags=["masjids"])


@masjid_router.get(ApiEndpoints.MASJID_NEARBY.value)
def get_masjid_nearby(
    latitude: float,
    longitude: float,
    radius: int = 1000,
    max_result_count: int = 10,
    client: GooglePlacesClient = Depends(get_places_client),
):
    try:
        data = client.search_nearby_masjid(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius,
            max_result_count=max_result_count,
        )
        return success_response(data)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value, detail=str(e)
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_SEARCH.value)
def search_masjid_by_name(
    q: str,
    max_result_count: int = 10,
    radius_meters: Optional[int] = Query(
        None,
        ge=500,
        le=50000,
        description=(
            "Radius in meters around the geocoded location (India). "
            "Default from MASJID_SEARCH_RADIUS_METERS env or 5000."
        ),
    ),
    client: GooglePlacesClient = Depends(get_places_client),
):
    try:
        if radius_meters is None:
            radius_meters = get_masjid_search_default_radius_meters()
        data = client.search_masjid_by_name(
            query=q,
            max_result_count=max_result_count,
            radius_meters=radius_meters,
        )
        return success_response(data)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value, detail=str(e)
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_BY_CITY.value)
def get_masjid_by_city(
    city: str,
    max_result_count: int = 20,
    radius_meters: Optional[int] = Query(
        None,
        ge=500,
        le=50000,
        description=(
            "Radius in meters around the geocoded city/area (India). "
            "Default from MASJID_SEARCH_RADIUS_METERS env or 5000."
        ),
    ),
    client: GooglePlacesClient = Depends(get_places_client),
):
    try:
        if radius_meters is None:
            radius_meters = get_masjid_search_default_radius_meters()
        data = client.search_masjid_by_city(
            city=city,
            max_result_count=max_result_count,
            radius_meters=radius_meters,
        )
        return success_response(data)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value, detail=str(e)
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_PLACE.value)
def get_masjid_place(
    place_id: str = Query(
        ...,
        description="Google Place ID",
    ),
    client: GooglePlacesClient = Depends(get_places_client),
):
    try:
        data = client.get_place_by_id(place_id)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST.value, detail=str(e))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_STATUS.value)
def get_masjid_status():
    enabled = is_masjid_module_enabled()
    return success_response({"enabled": enabled})
