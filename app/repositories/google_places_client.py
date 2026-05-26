from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, urlencode

from httpx import Client, ConnectError, HTTPStatusError, TimeoutException

from app.core.config import create_ssl_context
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.utils.photos import transform_photos_on_place, transform_places_in_search_response

_log = get_logger(__name__)

_GOOGLE_PLACES_PLACE_DETAILS_BASE = "https://places.googleapis.com/v1/places"
_GOOGLE_PLACES_SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
_GOOGLE_PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
_GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

_FIELD_MASK_SEARCH_NEARBY = (
    "places.id,places.name,places.displayName,places.formattedAddress,"
    "places.location,places.photos"
)
_FIELD_MASK_SEARCH_TEXT = (
    "places.id,places.name,places.displayName,places.formattedAddress,"
    "places.location,places.photos"
)
_FIELD_MASK_PLACE_DETAILS = (
    "id,displayName,formattedAddress,location,photos,name,"
    "currentOpeningHours,regularOpeningHours,internationalPhoneNumber,"
    "websiteUri,businessStatus,accessibilityOptions,paymentOptions,"
    "restroom,parkingOptions"
)


def _normalize_place_id(place_id: str) -> str:
    raw = (place_id or "").strip()
    if raw.startswith("places/"):
        raw = raw[len("places/"):]
    if not raw:
        raise ValueError("place_id is required")
    return raw


class GooglePlacesClient:
    def __init__(self, api_key: str, timeout: int = 10) -> None:
        self._api_key = (api_key or "").strip()
        self._timeout = timeout
        self._ssl_ctx = create_ssl_context()

    def _require_api_key(self) -> str:
        if not self._api_key:
            raise ApiException(
                "GOOGLE_PLACES_API_KEY is not configured.",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
                code="CONFIG_MISSING",
            )
        return self._api_key

    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        pid = _normalize_place_id(place_id)
        encoded = quote(pid, safe="")
        url = f"{_GOOGLE_PLACES_PLACE_DETAILS_BASE}/{encoded}"
        api_key = self._require_api_key()
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": _FIELD_MASK_PLACE_DETAILS,
        }
        data = self._get_json(url, headers)
        if isinstance(data, dict):
            transform_photos_on_place(data, api_key)
        return data

    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
            included_types: list,
            rank_preference: str,
    ) -> Dict[str, Any]:
        api_key = self._require_api_key()
        headers = self._search_headers(api_key, _FIELD_MASK_SEARCH_NEARBY)
        body: Dict[str, Any] = {
            "includedTypes": included_types,
            "maxResultCount": max_result_count,
            "rankPreference": rank_preference,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_meters,
                }
            },
        }
        return self._post_json(_GOOGLE_PLACES_SEARCH_NEARBY_URL, headers, body, api_key)

    def search_text(
            self,
            text_query: str,
            max_result_count: int,
            included_type: str,
            region_code: str,
            location_restriction: Dict[str, Any],
    ) -> Dict[str, Any]:
        api_key = self._require_api_key()
        headers = self._search_headers(api_key, _FIELD_MASK_SEARCH_TEXT)
        body: Dict[str, Any] = {
            "textQuery": text_query,
            "includedType": included_type,
            "maxResultCount": max_result_count,
            "regionCode": region_code,
            "locationRestriction": location_restriction,
        }
        return self._post_json(_GOOGLE_PLACES_SEARCH_TEXT_URL, headers, body, api_key)

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        q = (address or "").strip()
        if not q:
            return None
        params = {
            "address": q,
            "components": "country:IN",
            "region": "in",
            "key": self._require_api_key(),
        }
        url = f"{_GOOGLE_GEOCODE_URL}?{urlencode(params)}"
        try:
            with Client(timeout=self._timeout, verify=self._ssl_ctx) as client:
                response = client.get(url)
                response.raise_for_status()
                data: Dict[str, Any] = response.json()
        except (ConnectError, TimeoutException, HTTPStatusError) as exc:
            _log.warning("Geocoding failed: %s", exc)
            return None
        return self._extract_coords(data)

    @staticmethod
    def _search_headers(api_key: str, field_mask: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": field_mask,
        }

    @staticmethod
    def _extract_coords(data: Dict[str, Any]) -> Optional[Tuple[float, float]]:
        if data.get("status") != "OK":
            return None
        results = data.get("results") or []
        if not results:
            return None
        loc = (results[0].get("geometry") or {}).get("location") or {}
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat is None or lng is None:
            return None
        try:
            return float(lat), float(lng)
        except (TypeError, ValueError):
            return None

    def _get_json(self, url: str, headers: Dict[str, str]) -> Any:
        try:
            with Client(timeout=self._timeout, verify=self._ssl_ctx) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except ConnectError as exc:
            raise ApiException(
                "Cannot reach Google Places API.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code="SERVICE_UNAVAILABLE",
            ) from exc
        except TimeoutException:
            raise ApiException(
                "Google Places API timeout",
                status_code=HTTPStatus.GATEWAY_TIMEOUT.value,
                code="GATEWAY_TIMEOUT",
            )
        except HTTPStatusError as exc:
            self._handle_http_error(exc)

    def _post_json(
            self, url: str, headers: Dict[str, str], body: Dict[str, Any], api_key: str,
    ) -> Dict[str, Any]:
        try:
            with Client(timeout=self._timeout, verify=self._ssl_ctx) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()
                return transform_places_in_search_response(response.json(), api_key)
        except ConnectError as exc:
            raise ApiException(
                "Cannot reach Google Places API.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code="SERVICE_UNAVAILABLE",
            ) from exc
        except TimeoutException:
            raise ApiException(
                "Google Places API timeout",
                status_code=HTTPStatus.GATEWAY_TIMEOUT.value,
                code="GATEWAY_TIMEOUT",
            )
        except HTTPStatusError as exc:
            self._handle_http_error(exc)

    @staticmethod
    def _handle_http_error(exc: HTTPStatusError) -> None:
        if exc.response.status_code == HTTPStatus.NOT_FOUND.value:
            raise ApiException(
                "Place not found",
                status_code=HTTPStatus.NOT_FOUND.value,
                code="NOT_FOUND",
            ) from exc
        _log.error("Google Places error: %s", exc.response.text[:500])
        provider_msg: Optional[str] = None
        detail = f"Google Places API error: {exc.response.status_code}"
        try:
            err = exc.response.json().get("error") or {}
            api_msg = err.get("message") or err.get("status")
            if api_msg:
                detail = f"Google Places API: {api_msg}"
                provider_msg = api_msg
        except Exception:
            pass
        raise ApiException(
            detail,
            status_code=exc.response.status_code,
            provider_message=provider_msg,
        ) from exc
