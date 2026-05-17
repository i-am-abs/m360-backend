from __future__ import annotations

from typing import Any, Dict

from app.interfaces.cache_store import CacheStore
from app.interfaces.masjid_service import MasjidSearchService
from app.utils.cache_keys import create_normalized_geo_text, create_normalized_text_hash


class CachedMasjidSearchService(MasjidSearchService):
    def __init__(
            self,
            inner: MasjidSearchService,
            cache_store: CacheStore,
            ttl_seconds: int,
            key_prefix: str,
    ) -> None:
        self.inner = inner
        self.cache_store = cache_store
        self.ttl_seconds = max(1, ttl_seconds)
        self.key_prefix = (key_prefix or "m360").strip() or "m360"

    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        key = f"{self.key_prefix}:cache:masjid:place:{place_id.strip()}"
        hit = self.cache_store.get_json(key)
        if hit is not None:
            return hit
        data = self.inner.get_place_by_id(place_id)
        self.cache_store.set_json(key, data, self.ttl_seconds)
        return data

    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
    ) -> Dict[str, Any]:
        key = (
            f"{self.key_prefix}:cache:masjid:nearby:"
            f"{create_normalized_geo_text(latitude)}:{create_normalized_geo_text(longitude)}:"
            f"{radius_meters}:{max_result_count}"
        )
        hit = self.cache_store.get_json(key)
        if hit is not None:
            return hit
        data = self.inner.search_nearby(
            latitude, longitude, radius_meters, max_result_count,
        )
        self.cache_store.set_json(key, data, self.ttl_seconds)
        return data

    def search_by_name(
            self,
            query: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        qn = (query or "").strip().lower()
        key = (
            f"{self.key_prefix}:cache:masjid:name:{create_normalized_text_hash(qn)}:"
            f"{max_result_count}:{radius_meters}"
        )
        hit = self.cache_store.get_json(key)
        if hit is not None:
            return hit
        data = self.inner.search_by_name(query, max_result_count, radius_meters)
        self.cache_store.set_json(key, data, self.ttl_seconds)
        return data

    def search_by_city(
            self,
            city: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        cn = (city or "").strip().lower()
        key = (
            f"{self.key_prefix}:cache:masjid:city:{create_normalized_text_hash(cn)}:"
            f"{max_result_count}:{radius_meters}"
        )
        hit = self.cache_store.get_json(key)
        if hit is not None:
            return hit
        data = self.inner.search_by_city(city, max_result_count, radius_meters)
        self.cache_store.set_json(key, data, self.ttl_seconds)
        return data
