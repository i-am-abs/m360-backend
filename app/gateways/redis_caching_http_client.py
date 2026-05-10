from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from app.interfaces.http_client import HttpClient


class RedisCachingHttpClient(HttpClient):
    def __init__(
            self,
            inner: HttpClient,
            redis_client: Any,
            ttl_seconds: int,
            key_prefix: str,
    ) -> None:
        self._inner = inner
        self._redis = redis_client
        self._ttl = max(1, ttl_seconds)
        self._pfx = (key_prefix or "m360").strip() or "m360"

    def _cache_key(self, url: str, params: Optional[Dict[str, Any]]) -> str:
        canonical = json.dumps(params or {}, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{url}\n{canonical}".encode()).hexdigest()
        return f"{self._pfx}:cache:http:get:{digest}"

    def get(
            self,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        key = self._cache_key(url, params)
        cached = self._redis.get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        data = self._inner.get(url, headers, params)
        try:
            self._redis.setex(key, self._ttl, json.dumps(data, default=str))
        except TypeError:
            pass
        return data
