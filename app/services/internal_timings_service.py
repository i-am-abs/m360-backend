from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from redis import Redis

from app.interfaces.masjid_repository import MasjidRepository
from app.schemas.masjid_content import MasjidTimingsResponse, PrayerTimingItem
from app.utils.structured_log import log_event, log_timing


class InternalTimingsService:
    """High-frequency read path with Redis caching."""

    def __init__(
        self,
        masjid_store: MasjidRepository,
        redis_client: Optional[Redis] = None,
        cache_ttl_seconds: int = 60,
        cache_key_prefix: str = "m360",
    ) -> None:
        self._masjid_store = masjid_store
        self._redis = redis_client
        self._cache_ttl = cache_ttl_seconds
        self._cache_prefix = cache_key_prefix

    def get_timings(self, place_id: str) -> MasjidTimingsResponse:
        cache_key = self._cache_key(place_id)
        cached = self._cache_get(cache_key)
        if cached is not None:
            log_event("internal_timings", "cache_hit", resource_id=place_id)
            return MasjidTimingsResponse(**cached)

        log_event("internal_timings", "cache_miss", resource_id=place_id)
        with log_timing("internal_timings", "fetch", resource_id=place_id):
            raw = self._masjid_store.get_timings(place_id) or []
            timings = [PrayerTimingItem(**item) for item in raw]
            response = MasjidTimingsResponse(place_id=place_id, timings=timings)

        self._cache_set(cache_key, response.model_dump(by_alias=True))
        return response

    def _cache_key(self, place_id: str) -> str:
        digest = hashlib.sha256(place_id.encode()).hexdigest()
        return f"{self._cache_prefix}:cache:internal:timings:{digest}"

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        if self._redis is None or self._cache_ttl <= 0:
            return None
        try:
            raw = self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            return None
        return None

    def _cache_set(self, key: str, value: Dict[str, Any]) -> None:
        if self._redis is None or self._cache_ttl <= 0:
            return
        try:
            self._redis.setex(key, self._cache_ttl, json.dumps(value))
        except Exception:
            pass
