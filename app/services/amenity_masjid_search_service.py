from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.utils.amenities import apply_amenity_fields
from app.utils.masjid import normalize_place_id


class AmenityMasjidSearchService(MasjidSearchService):
    """Decorates search results with stored masjid amenities."""

    def __init__(
            self,
            inner: MasjidSearchService,
            masjid_store: Optional[MasjidRepository],
    ) -> None:
        self._inner = inner
        self._masjid_store = masjid_store

    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        place = self._inner.get_place_by_id(place_id)
        self._attach([place] if isinstance(place, dict) else [])
        return place

    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
    ) -> Dict[str, Any]:
        data = self._inner.search_nearby(
            latitude, longitude, radius_meters, max_result_count,
        )
        self._attach(data.get("places") or [])
        return data

    def search_by_name(
            self,
            query: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        data = self._inner.search_by_name(query, max_result_count, radius_meters)
        self._attach(data.get("places") or [])
        return data

    def search_by_city(
            self,
            city: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        data = self._inner.search_by_city(city, max_result_count, radius_meters)
        self._attach(data.get("places") or [])
        return data

    def _attach(self, places: List[Any]) -> None:
        for place in places:
            if not isinstance(place, dict):
                continue
            try:
                pid = normalize_place_id(
                    str(place.get("id") or place.get("place_id") or ""),
                )
                stored = None
                if pid and self._masjid_store is not None:
                    stored = self._masjid_store.get_amenities(pid)
                apply_amenity_fields(place, stored)
            except Exception:
                apply_amenity_fields(place, None)
