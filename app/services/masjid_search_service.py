from __future__ import annotations

from http import HTTPStatus
from math import inf
from typing import Any, Dict, Optional, Tuple

from app.core.enums.error_code import ErrorCode
from app.core.enums.google_places import GooglePlacesPayload
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.masjid_service import MasjidSearchService
from app.repositories.google_places_client import GooglePlacesClient
from app.utils.geo import haversine_meters, india_location_restriction_rectangle, is_point_in_india

_log = get_logger(__name__)


class GoogleMasjidSearchService(MasjidSearchService):
    def __init__(self, places_client: GooglePlacesClient) -> None:
        self._client = places_client

    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        return self._client.get_place_details(place_id)

    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
    ) -> Dict[str, Any]:
        if not is_point_in_india(latitude, longitude):
            raise ApiException(
                "Masjid search is limited to India.",
                status_code=HTTPStatus.BAD_REQUEST.value,
                code=ErrorCode.LOCATION_OUT_OF_BOUNDS,
            )
        data = self._client.search_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            max_result_count=max_result_count,
            included_types=[GooglePlacesPayload.PLACE_TYPE_MOSQUE.value],
            rank_preference=GooglePlacesPayload.RANK_DISTANCE.value,
        )
        data = self._filter_to_india(data)
        return self._enrich_distance_and_sort(data, latitude, longitude)

    def search_by_name(
            self,
            query: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"places": []}
        q = query.strip()

        coords: Optional[Tuple[float, float]] = self._client.geocode(q)
        if coords:
            lat, lng = coords
            if is_point_in_india(lat, lng):
                return self.search_nearby(lat, lng, radius_meters, max_result_count)

        return self._text_search(f"mosque in {q}", max_result_count)

    def search_by_city(
            self,
            city: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        return self.search_by_name(city, max_result_count, radius_meters)

    def _text_search(self, text_query: str, max_result_count: int) -> Dict[str, Any]:
        data = self._client.search_text(
            text_query=text_query,
            max_result_count=max_result_count,
            included_type=GooglePlacesPayload.PLACE_TYPE_MOSQUE.value,
            region_code=GooglePlacesPayload.REGION_INDIA.value,
            location_restriction=india_location_restriction_rectangle(),
        )
        return self._filter_to_india(data)

    @staticmethod
    def _filter_to_india(data: Dict[str, Any]) -> Dict[str, Any]:
        kept = []
        for p in data.get("places") or []:
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
    def _enrich_distance_and_sort(
            data: Dict[str, Any], origin_lat: float, origin_lng: float,
    ) -> Dict[str, Any]:
        for p in data.get("places") or []:
            if not isinstance(p, dict):
                continue
            d = _compute_distance(p, origin_lat, origin_lng)
            if d is not None:
                p["distanceMeters"] = d
        data["places"] = sorted(
            data.get("places") or [],
            key=lambda p: p.get("distanceMeters", inf) if isinstance(p, dict) else inf,
        )
        return data


def _compute_distance(place: Dict[str, Any], o_lat: float, o_lng: float) -> Optional[int]:
    raw = place.get("straightLineDistanceMeters")
    if raw is not None:
        try:
            return int(round(float(raw)))
        except (TypeError, ValueError):
            pass
    loc = place.get("location") or {}
    try:
        return int(round(haversine_meters(o_lat, o_lng, float(loc["latitude"]), float(loc["longitude"]))))
    except (TypeError, ValueError, KeyError):
        return None
