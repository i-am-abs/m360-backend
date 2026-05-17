from __future__ import annotations

import json
from typing import Any, Optional

from app.gateways.strict_redis_client import StrictRedisClient
from app.interfaces.cache_store import CacheStore


class RedisCacheStore(CacheStore):
    def __init__(self, redis_client: StrictRedisClient) -> None:
        self.redis_client = redis_client

    def get_json(self, key: str) -> Optional[Any]:
        raw_value = self.redis_client.get(key)
        if not raw_value:
            return None
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))

    def delete(self, key: str) -> None:
        self.redis_client.delete(key)

    def ping(self) -> bool:
        return self.redis_client.ping()

    def close(self) -> None:
        self.redis_client.close()
