from typing import Any, Dict, Optional
from urllib.parse import quote

from httpx import Client, ConnectError, HTTPStatusError, TimeoutException

from constants.google_places_config import GooglePlacesConfig
from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from logger.Logger import Logger
from utils.google_places import (
    get_google_places_api_key,
    normalize_place_id_for_path,
    transform_photos_on_place,
    transform_places_in_search_response,
)

logger = Logger.get_logger(__name__)


class GooglePlacesClient:
    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        pid = normalize_place_id_for_path(place_id)
        encoded = quote(pid, safe="")
        url = f"{GooglePlacesConfig.PLACE_DETAILS_BASE.value}/{encoded}"
        api_key = get_google_places_api_key()
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": GooglePlacesConfig.PLACE_DETAILS_FIELD_MASK.value,
        }
        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    transform_photos_on_place(data, api_key)
                return data
        except ConnectError as e:
            logger.error("Google Places API unreachable: %s", e)
            raise ApiException(
                "Cannot reach Google Places API. Check network.",
                status_code=503,
            ) from e
        except TimeoutException:
            raise ApiException("Google Places API timeout", status_code=504)
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ApiException("Place not found", status_code=404) from e
            logger.error("Google Places API error: %s", e.response.text)
            raise ApiException(
                f"Google Places API error: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e

    def search_nearby_masjid(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int = 1000,
            max_result_count: int = 10,
    ) -> Dict[str, Any]:
        api_key = get_google_places_api_key()
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": GooglePlacesConfig.SEARCH_FIELD_MASK.value,
        }
        body = {
            "includedTypes": ["mosque"],
            "maxResultCount": max_result_count,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius_meters,
                }
            },
        }
        return self._post_places(
            GooglePlacesConfig.SEARCH_NEARBY_URL.value,
            headers,
            body,
            api_key,
        )

    def search_masjid_by_name(
            self,
            query: str,
            max_result_count: int = 10,
    ) -> Dict[str, Any]:
        if not query:
            return {"places": []}
        api_key = get_google_places_api_key()
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": GooglePlacesConfig.SEARCH_FIELD_MASK.value,
        }
        body = {
            "textQuery": query,
            "includedType": "mosque",
            "maxResultCount": max_result_count,
        }
        return self._post_places(
            GooglePlacesConfig.SEARCH_TEXT_URL.value,
            headers,
            body,
            api_key,
        )

    def search_masjid_by_city(
            self,
            city: str,
            max_result_count: int = 20,
    ) -> Dict[str, Any]:
        if not city:
            return {"places": []}
        api_key = get_google_places_api_key()
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": GooglePlacesConfig.SEARCH_FIELD_MASK.value,
        }
        body = {
            "textQuery": f"mosque in {city}",
            "includedType": "mosque",
            "maxResultCount": max_result_count,
        }
        return self._post_places(
            GooglePlacesConfig.SEARCH_TEXT_URL.value,
            headers,
            body,
            api_key,
        )

    def _post_places(
            self,
            url: str,
            headers: Dict[str, str],
            body: Dict[str, Any],
            api_key: str,
    ) -> Dict[str, Any]:
        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                return transform_places_in_search_response(data, api_key)
        except ConnectError as e:
            logger.error("Google Places API unreachable: %s", e)
            raise ApiException(
                "Cannot reach Google Places API. Check network.",
                status_code=503,
            ) from e
        except TimeoutException:
            raise ApiException("Google Places API timeout", status_code=504)
        except HTTPStatusError as e:
            logger.error("Google Places API error: %s", e.response.text)
            raise ApiException(
                f"Google Places API error: {e.response.status_code}",
                status_code=e.response.status_code,
            )


_places_client: Optional[GooglePlacesClient] = None


def get_places_client() -> GooglePlacesClient:
    global _places_client
    if _places_client is None:
        _places_client = GooglePlacesClient()
    return _places_client
