from typing import Any, Optional
from datetime import datetime, timedelta
from db.cache_provider import CacheProvider
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class LocalCacheProvider(CacheProvider):

    def __init__(self):
        self.cache = {}
        logger.info("LocalCacheProvider initialized - using in-memory storage")

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            cache_entry = self.cache[key]
            if cache_entry["expiry"] > datetime.now():
                logger.debug(f"[LOCAL CACHE] HIT: {key}")
                return cache_entry["value"]
            else:
                del self.cache[key]
                logger.debug(f"[LOCAL CACHE] EXPIRED: {key}")

        logger.debug(f"[LOCAL CACHE] MISS: {key}")
        return None

    def set(self, key: str, value: Any, ttl: int) -> bool:
        try:
            expiry = datetime.now() + timedelta(seconds=ttl)
            self.cache[key] = {"value": value, "expiry": expiry}
            logger.debug(f"[LOCAL CACHE] SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"[LOCAL CACHE] SET error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"[LOCAL CACHE] DELETE: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"[LOCAL CACHE] DELETE error for key {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        try:
            pattern_prefix = pattern.replace("*", "")
            matching_keys = [k for k in self.cache.keys() if pattern_prefix in k]

            for key in matching_keys:
                del self.cache[key]

            return len(matching_keys)
        except Exception as e:
            logger.error(
                f"[LOCAL CACHE] CLEAR_PATTERN error for pattern {pattern}: {e}"
            )
            return 0

    def size(self) -> int:
        return len(self.cache)

    def clear_all(self) -> int:
        size = len(self.cache)
        self.cache.clear()
        logger.info(f"[LOCAL CACHE] Cleared all {size} entries")
        return size
