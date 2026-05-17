from __future__ import annotations

import time
from threading import RLock
from typing import Any, Dict, Optional

from app.interfaces.cache_store import CacheStore


class LocalCacheStore(CacheStore):
    def __init__(self) -> None:
        self.lock = RLock()
        self.items: Dict[str, Dict[str, Any]] = {}

    def get_json(self, key: str) -> Optional[Any]:
        with self.lock:
            item = self.items.get(key)
            if item is None:
                return None
            if float(item["expires_at"]) <= time.time():
                del self.items[key]
                return None
            return item["value"]

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self.lock:
            self.items[key] = {
                "value": value,
                "expires_at": time.time() + max(1, int(ttl_seconds)),
            }

    def delete(self, key: str) -> None:
        with self.lock:
            self.items.pop(key, None)

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        with self.lock:
            self.items.clear()
