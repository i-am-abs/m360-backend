from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from app.interfaces.masjid_service import MasjidSearchService


def _stable_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:32]


def _geo_part(x: float) -> str:
    return f"{round(float(x), 5):.5f}"


class CachedMasjidSearchService(MasjidSearchService):
    def __init__(
            self,
            inner: MasjidSearchService,
            redis_client: Any,
            ttl_seconds: int,
            key_prefix: str,
    ) -> None:
        self._inner = inner
        self._redis = redis_client
        self._ttl = max(1, ttl_seconds)
        self._pfx = (key_prefix or "m360").strip() or "m360"

    def _get_json(self, key: str) -> Optional[Any]:
        raw = self._redis.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _set_json(self, key: str, value: Any) -> None:
        self._redis.setex(key, self._ttl, json.dumps(value, default=str))

    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        key = f"{self._pfx}:cache:masjid:place:{place_id.strip()}"
        hit = self._get_json(key)
        if hit is not None:
            return hit
        data = self._inner.get_place_by_id(place_id)
        self._set_json(key, data)
        return data

    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
    ) -> Dict[str, Any]:
        key = (
            f"{self._pfx}:cache:masjid:nearby:"
            f"{_geo_part(latitude)}:{_geo_part(longitude)}:{radius_meters}:{max_result_count}"
        )
        hit = self._get_json(key)
        if hit is not None:
            return hit
        data = self._inner.search_nearby(
            latitude, longitude, radius_meters, max_result_count,
        )
        self._set_json(key, data)
        return data

    def search_by_name(
            self,
            query: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        qn = (query or "").strip().lower()
        key = (
            f"{self._pfx}:cache:masjid:name:{_stable_hash(qn)}:"
            f"{max_result_count}:{radius_meters}"
        )
        hit = self._get_json(key)
        if hit is not None:
            return hit
        data = self._inner.search_by_name(query, max_result_count, radius_meters)
        self._set_json(key, data)
        return data

    def search_by_city(
            self,
            city: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        cn = (city or "").strip().lower()
        key = (
            f"{self._pfx}:cache:masjid:city:{_stable_hash(cn)}:"
            f"{max_result_count}:{radius_meters}"
        )
        hit = self._get_json(key)
        if hit is not None:
            return hit
        data = self._inner.search_by_city(city, max_result_count, radius_meters)
        self._set_json(key, data)
        return data
