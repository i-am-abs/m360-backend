from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Tuple

from redis import Redis

from app.utils.structured_log import log_event


class RateLimitBackend(ABC):
    @abstractmethod
    def check_and_increment(
            self,
            key: str,
            limit: int,
            window_seconds: int,
    ) -> Tuple[bool, int]:
        pass


class RedisRateLimitBackend(RateLimitBackend):
    def __init__(self, redis_client: Redis, key_prefix: str) -> None:
        self._redis = redis_client
        self._prefix = key_prefix

    def check_and_increment(
            self,
            key: str,
            limit: int,
            window_seconds: int,
    ) -> Tuple[bool, int]:
        redis_key = f"{self._prefix}:ratelimit:{key}"
        try:
            count = int(self._redis.incr(redis_key))
            if count == 1:
                self._redis.expire(redis_key, window_seconds)
            ttl = int(self._redis.ttl(redis_key))
            retry_after = max(ttl, 1) if ttl > 0 else window_seconds
            return count <= limit, retry_after
        except Exception as exc:
            log_event(
                "rate_limit",
                "redis_backend_error",
                level="warning",
                error=str(exc),
            )
            return True, 0


class InMemoryRateLimitBackend(RateLimitBackend):
    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check_and_increment(
            self,
            key: str,
            limit: int,
            window_seconds: int,
    ) -> Tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
        return True, 0


class RateLimiter:
    def __init__(
            self,
            backend: RateLimitBackend,
            *,
            default_limit: int,
            auth_limit: int,
            window_seconds: int = 60,
    ) -> None:
        self._backend = backend
        self._default_limit = default_limit
        self._auth_limit = auth_limit
        self._window_seconds = window_seconds

    def check(self, client_key: str, path: str) -> Tuple[bool, int]:
        limit = self._auth_limit if self._is_auth_path(path) else self._default_limit
        allowed, retry_after = self._backend.check_and_increment(
            f"{client_key}:{self._bucket(path)}",
            limit,
            self._window_seconds,
        )
        if not allowed:
            log_event(
                "rate_limit",
                "limit_exceeded",
                resource_id=client_key,
                path=path,
                limit=limit,
                retry_after_seconds=retry_after,
            )
        return allowed, retry_after

    @staticmethod
    def _is_auth_path(path: str) -> bool:
        normalized = path.rstrip("/")
        return (
                "/auth/" in normalized
                or normalized.endswith("/auth")
                or "/auth/phone/" in normalized
        )

    @staticmethod
    def _bucket(path: str) -> str:
        return "auth" if RateLimiter._is_auth_path(path) else "default"
