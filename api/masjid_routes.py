from fastapi import APIRouter, Depends, HTTPException, Query

from client.google_places_client import GooglePlacesClient, get_places_client
from constants.api_endpoints import ApiEndpoints
from exceptions.api_exception import ApiException
from utils.google_places import is_masjid_module_enabled
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
        raise HTTPException(status_code=500, detail=str(e))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_SEARCH.value)
def search_masjid_by_name(
        q: str,
        max_result_count: int = 10,
        client: GooglePlacesClient = Depends(get_places_client),
):
    try:
        data = client.search_masjid_by_name(query=q, max_result_count=max_result_count)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_BY_CITY.value)
def get_masjid_by_city(
        city: str,
        max_result_count: int = 20,
        client: GooglePlacesClient = Depends(get_places_client),
):
    try:
        data = client.search_masjid_by_city(
            city=city,
            max_result_count=max_result_count,
        )
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_PLACE.value)
def get_masjid_place(
        place_id: str = Query(
            ...,
            description="Google Place ID (e.g. ChIJ...) or full resource name places/ChIJ...",
        ),
        client: GooglePlacesClient = Depends(get_places_client),
):
    try:
        data = client.get_place_by_id(place_id)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@masjid_router.get(ApiEndpoints.MASJID_STATUS.value)
def get_masjid_status():
    enabled = is_masjid_module_enabled()
    return success_response({"enabled": enabled})
