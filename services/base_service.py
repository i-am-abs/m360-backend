from hashlib import md5
from constants.cache_config import CacheConfig
from db.factory.cache_factory import CacheFactory
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class BaseService:
    def __init__(self, config, token_provider, http_client):
        self.config = config
        self.token_provider = token_provider
        self.http_client = http_client
        self.cache = CacheFactory.create()

    def _generate_cache_key(self, endpoint: str, params: dict) -> str:
        params_str = str(sorted(params.items()))
        key_str = f"{endpoint}:{params_str}"
        return f"quran_api:{md5(key_str.encode()).hexdigest()}"

    def _get(self, endpoint, params=None):
        params = params or {}

        cache_key = self._generate_cache_key(endpoint, params)
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            token = self.token_provider.get_access_token()
            headers = {
                "x-auth-token": token,
                "x-client-id": self.config.client_id,
            }

            data = self.http_client.get(
                f"{self.config.base_url}{endpoint}",
                headers=headers,
                params=params,
            )

            self.cache.set(cache_key, data, ttl=CacheConfig.TTL_EXPIRATION.value)
            return data

        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            raise
