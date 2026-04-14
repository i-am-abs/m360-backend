from http import HTTPStatus
from math import inf
from typing import Any, Dict, Optional, Protocol, Tuple
from urllib.parse import quote

from httpx import Client, ConnectError, HTTPStatusError, TimeoutException

from constants.geo import india_location_restriction_rectangle, is_point_in_india
from constants.google_places_config import GooglePlacesConfig, GooglePlacesPayload
from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from logger.Logger import Logger
from services.google_places.support.distance import haversine_meters
from services.google_places.support.env import get_google_places_api_key
from services.google_places.support.geocoding import geocode_in_india
from services.google_places.support.photos import (
    transform_photos_on_place,
    transform_places_in_search_response,
)
from services.google_places.support.place_id import normalize_place_id_for_path

logger = Logger.get_logger(__name__)


class MasjidPlacesService(Protocol):
    def get_place_by_id(self, place_id: str) -> Dict[str, Any]: ...

    def search_nearby_masjid(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int = 1000,
            max_result_count: int = 10,
    ) -> Dict[str, Any]: ...

    def search_masjid_by_name(
            self,
            query: str,
            max_result_count: int = 10,
            radius_meters: int = 5000,
    ) -> Dict[str, Any]: ...

    def search_masjid_by_city(
            self,
            city: str,
            max_result_count: int = 20,
            radius_meters: int = 5000,
    ) -> Dict[str, Any]: ...


class GoogleMasjidPlacesService:
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
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            ) from e
        except TimeoutException:
            raise ApiException(
                "Google Places API timeout",
                status_code=HTTPStatus.GATEWAY_TIMEOUT.value,
            )
        except HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND.value:
                raise ApiException(
                    "Place not found",
                    status_code=HTTPStatus.NOT_FOUND.value,
                ) from e
            logger.error("Google Places API error: %s", e.response.text)
            raise ApiException(
                f"Google Places API error: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e

    @staticmethod
    def _filter_places_to_india(data: Dict[str, Any]) -> Dict[str, Any]:
        places = data.get("places") or []
        kept = []
        for p in places:
            if not isinstance(p, dict):
                continue
            loc = p.get("location") or {}
            lat, lng = loc.get("latitude"), loc.get("longitude")
            if lat is None or lng is None:
                continue
            try:
                if is_point_in_india(float(lat), float(lng)):
                    kept.append(p)
            except (TypeError, ValueError):
                continue
        data["places"] = kept
        return data

    @staticmethod
    def _enrich_distance_meters_and_sort(
            data: Dict[str, Any],
            origin_lat: float,
            origin_lng: float,
    ) -> Dict[str, Any]:
        places = data.get("places") or []

        def distance_for(place: Dict[str, Any]) -> Optional[int]:
            raw = place.get("straightLineDistanceMeters")
            if raw is not None:
                try:
                    return int(round(float(raw)))
                except (TypeError, ValueError):
                    pass
            loc = place.get("location") or {}
            try:
                plat = float(loc.get("latitude"))
                plng = float(loc.get("longitude"))
            except (TypeError, ValueError):
                return None
            return int(round(haversine_meters(origin_lat, origin_lng, plat, plng)))

        for p in places:
            if isinstance(p, dict):
                d = distance_for(p)
                if d is not None:
                    p["distanceMeters"] = d

        def sort_key(p: Any) -> float:
            if not isinstance(p, dict):
                return inf
            dm = p.get("distanceMeters")
            if dm is None:
                return inf
            try:
                return float(dm)
            except (TypeError, ValueError):
                return inf

        data["places"] = sorted(places, key=sort_key)
        return data

    def search_nearby_masjid(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int = 1000,
            max_result_count: int = 10,
    ) -> Dict[str, Any]:
        if not is_point_in_india(latitude, longitude):
            raise ApiException(
                "Masjid search is limited to India, You have provided wrong Data.",
                status_code=HTTPStatus.BAD_REQUEST.value,
            )
        api_key = get_google_places_api_key()
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": GooglePlacesConfig.SEARCH_NEARBY_FIELD_MASK.value,
        }
        body: Dict[str, Any] = {
            "includedTypes": [GooglePlacesPayload.PLACE_TYPE_MOSQUE],
            "maxResultCount": max_result_count,
            "rankPreference": GooglePlacesPayload.RANK_PREFERENCE_DISTANCE,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_meters,
                }
            },
        }
        data = self._post_places(
            GooglePlacesConfig.SEARCH_NEARBY_URL.value,
            headers,
            body,
            api_key,
        )
        data = self._filter_places_to_india(data)
        return self._enrich_distance_meters_and_sort(data, latitude, longitude)

    def _text_search_mosques(
            self,
            text_query: str,
            max_result_count: int,
            api_key: str,
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": GooglePlacesConfig.SEARCH_TEXT_FIELD_MASK.value,
        }
        body: Dict[str, Any] = {
            "textQuery": text_query,
            "includedType": GooglePlacesPayload.PLACE_TYPE_MOSQUE,
            "maxResultCount": max_result_count,
            "regionCode": GooglePlacesPayload.REGION_CODE_INDIA,
            "locationRestriction": india_location_restriction_rectangle(),
        }
        data = self._post_places(
            GooglePlacesConfig.SEARCH_TEXT_URL.value,
            headers,
            body,
            api_key,
        )
        return self._filter_places_to_india(data)

    def search_masjid_by_name(
            self,
            query: str,
            max_result_count: int = 10,
            radius_meters: int = 5000,
    ) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"places": []}
        q = query.strip()
        api_key = get_google_places_api_key()

        coords: Optional[Tuple[float, float]] = geocode_in_india(q, api_key)
        if coords:
            lat, lng = coords
            if is_point_in_india(lat, lng):
                return self.search_nearby_masjid(
                    latitude=lat,
                    longitude=lng,
                    radius_meters=radius_meters,
                    max_result_count=max_result_count,
                )

        return self._text_search_mosques(
            text_query=f"mosque in {q}",
            max_result_count=max_result_count,
            api_key=api_key,
        )

    def search_masjid_by_city(
            self,
            city: str,
            max_result_count: int = 20,
            radius_meters: int = 5000,
    ) -> Dict[str, Any]:
        return self.search_masjid_by_name(
            query=city,
            max_result_count=max_result_count,
            radius_meters=radius_meters,
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
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            ) from e
        except TimeoutException:
            raise ApiException(
                "Google Places API timeout",
                status_code=HTTPStatus.GATEWAY_TIMEOUT.value,
            )
        except HTTPStatusError as e:
            body_txt = e.response.text
            logger.error(
                "Google Places API error %s: %s",
                e.response.status_code,
                body_txt,
            )
            detail = f"Google Places API error: {e.response.status_code}"
            try:
                err = e.response.json().get("error") or {}
                api_msg = err.get("message") or err.get("status")
                if api_msg:
                    detail = f"Google Places API: {api_msg}"
            except Exception:
                pass
            raise ApiException(detail, status_code=e.response.status_code) from e
