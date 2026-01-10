import redis
import json
import os
from typing import Any, Optional

from constants.system_config import SystemConfig
from db.cache_provider import CacheProvider
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class RedisCacheProvider(CacheProvider):
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD", None)

        timeout = SystemConfig.REDIS_CONNECTION_TIMEOUT.value

        try:
            self.client = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=timeout,
                socket_timeout=timeout,
            )
            self.client.ping()
            logger.info(f"Connected to Redis: {redis_host}:{redis_port}")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise ConnectionError(
                f"Failed to connect to Redis at {redis_host}:{redis_port}"
            )

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {key}, {e}")
            return None

    def set(self, key: str, value: Any, ttl: int) -> bool:
        try:
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {key}, {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            result = self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {key}, {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear_pattern error: {pattern}, {e}")
            return 0

    def exists(self, key: str) -> bool:
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {key}, {e}")
            return False

    def ttl(self, key: str) -> int:
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl error: {key}, {e}")
            return -1

    def ping(self) -> bool:
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
