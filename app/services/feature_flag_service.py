from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from redis import Redis

from app.interfaces.feature_flag_repository import FeatureFlagRepository
from app.services.feature_flag_strategies import (
    CoordinateStrategy,
    DefaultStrategy,
    FeatureResolutionStrategy,
    LocationKeyStrategy,
    RegionStrategy,
    merge_features,
)
from app.utils.structured_log import log_event, log_timing


class FeatureFlagService:
    def __init__(
            self,
            store: FeatureFlagRepository,
            redis_client: Optional[Redis] = None,
            cache_ttl_seconds: int = 300,
            cache_key_prefix: str = "m360",
    ) -> None:
        self._store = store
        self._redis = redis_client
        self._cache_ttl = cache_ttl_seconds
        self._cache_prefix = cache_key_prefix
        self._strategies: list[FeatureResolutionStrategy] = [
            LocationKeyStrategy(store),
            CoordinateStrategy(store),
            RegionStrategy(store),
            DefaultStrategy(store),
        ]

    def get_features(self, **context: Any) -> Dict[str, bool]:
        cache_key = self._cache_key(context)
        cached = self._cache_get(cache_key)
        if cached is not None:
            log_event("feature_flags", "cache_hit", resource_id=cache_key)
            return cached

        log_event("feature_flags", "cache_miss", resource_id=cache_key)
        with log_timing("feature_flags", "resolve", **context):
            doc = self._resolve(context)
            features = merge_features(doc)
        self._cache_set(cache_key, features)
        log_event("feature_flags", "resolved", features=features, **context)
        return features

    def _resolve(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for strategy in self._strategies:
            doc = strategy.resolve(context)
            if doc:
                return doc
        return None

    def _cache_key(self, context: Dict[str, Any]) -> str:
        raw = json.dumps(context, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"{self._cache_prefix}:cache:features:{digest}"

    def _cache_get(self, key: str) -> Optional[Dict[str, bool]]:
        if self._redis is None or self._cache_ttl <= 0:
            return None
        try:
            raw = self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            return None
        return None

    def _cache_set(self, key: str, value: Dict[str, bool]) -> None:
        if self._redis is None or self._cache_ttl <= 0:
            return
        try:
            self._redis.setex(key, self._cache_ttl, json.dumps(value))
        except Exception:
            pass
