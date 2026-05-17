from __future__ import annotations

from typing import Any, Dict, Optional

from app.interfaces.cache_store import CacheStore
from app.interfaces.http_client import HttpClient
from app.utils.cache_keys import create_http_get_cache_key


class RedisCachingHttpClient(HttpClient):
    def __init__(
            self,
            inner: HttpClient,
            cache_store: CacheStore,
            ttl_seconds: int,
            key_prefix: str,
    ) -> None:
        self.inner = inner
        self.cache_store = cache_store
        self.ttl_seconds = max(1, ttl_seconds)
        self.key_prefix = (key_prefix or "m360").strip() or "m360"

    def get(
            self,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        key = create_http_get_cache_key(self.key_prefix, url, params)
        cached = self.cache_store.get_json(key)
        if cached is not None:
            return cached
        data = self.inner.get(url, headers, params)
        self.cache_store.set_json(key, data, self.ttl_seconds)
        return data
