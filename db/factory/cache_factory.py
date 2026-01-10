import os

from db.cache_provider import CacheProvider
from db.impl.local_cache_provider import LocalCacheProvider
from db.impl.redis_cache_provider import RedisCacheProvider
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class CacheFactory:
    _cache_instance = None

    @staticmethod
    def create() -> CacheProvider:
        if CacheFactory._cache_instance is not None:
            return CacheFactory._cache_instance

        use_redis = os.getenv("REDIS", "false").lower() in ("true", "1", "yes")

        if use_redis:
            try:
                CacheFactory._cache_instance = RedisCacheProvider()
                logger.info("Using Redis cache")
            except ConnectionError as e:
                logger.error(f"Redis connection failed: {e}, using local cache")
                CacheFactory._cache_instance = LocalCacheProvider()
        else:
            CacheFactory._cache_instance = LocalCacheProvider()

        return CacheFactory._cache_instance

    @staticmethod
    def reset():
        CacheFactory._cache_instance = None
