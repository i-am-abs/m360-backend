from __future__ import annotations

from typing import Optional

from redis import Redis

from app.core.config import Settings
from app.gateways.http_client import HttpxClient
from app.gateways.oauth_token_provider import OAuthTokenProvider
from app.gateways.redis_caching_http_client import RedisCachingHttpClient
from app.interfaces.http_client import HttpClient
from app.interfaces.token_provider import TokenProvider
from app.modules.quran.facade.quran_module_facade import QuranModuleFacade
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService


class QuranModuleConfiguration:
    def __init__(
            self,
            settings: Settings,
            redisClient: Optional[Redis],
            redisCacheModuleActive: bool,
    ) -> None:
        self.settings = settings
        self.redisClient = redisClient
        self.redisCacheModuleActive = redisCacheModuleActive

    def createFacade(self) -> QuranModuleFacade:
        provider: TokenProvider = OAuthTokenProvider(self.settings)
        httpInnerClient = HttpxClient(timeout=self.settings.request_timeout_seconds)

        if (
                self.redisCacheModuleActive
                and self.redisClient is not None
                and self.settings.api_get_cache_ttl_seconds > 0
        ):
            httpClient: HttpClient = RedisCachingHttpClient(
                httpInnerClient,
                self.redisClient,
                self.settings.api_get_cache_ttl_seconds,
                self.settings.redis_key_prefix,
            )
        else:
            httpClient = httpInnerClient

        return QuranModuleFacade(
            quranApiClient=QuranApiClient(self.settings, provider, httpClient),
            quranOAuthService=QuranOAuthService(provider),
        )
