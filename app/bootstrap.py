from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pymongo import MongoClient

from app.core.config import Settings
from app.core.logging import get_logger
from app.gateways.http_client import HttpxClient
from app.gateways.msg91_gateway import Msg91OtpGateway
from app.gateways.oauth_token_provider import OAuthTokenProvider
from app.gateways.redis_caching_http_client import RedisCachingHttpClient
from app.gateways.strict_redis_client import StrictRedisClient
from app.integrations.msg91_pending_req import Msg91PendingReqIdStore
from app.interfaces.cache_store import CacheStore
from app.interfaces.http_client import HttpClient
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.token_provider import TokenProvider
from app.interfaces.user_repository import UserRepository
from app.repositories.google_places_client import GooglePlacesClient
from app.repositories.local_cache_store import LocalCacheStore
from app.repositories.local_cache_user_store import LocalCacheUserStore
from app.repositories.mongo_user_store import MongoUserStore
from app.repositories.redis_cache_store import RedisCacheStore
from app.repositories.redis_user_store import RedisUserStore
from app.services.cached_masjid_search_service import CachedMasjidSearchService
from app.services.masjid_search_service import GoogleMasjidSearchService
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.user_masjid_service import UserMasjidService
from app.utils.phone import IndiaPhoneValidator

log = get_logger(__name__)


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def create_redis_client(settings: Settings) -> Optional[StrictRedisClient]:
    if settings.local_mode:
        return None
    redis_client = StrictRedisClient(
        master_urls=settings.redis_master_urls,
        slave_urls=settings.redis_slave_urls,
        decode_responses=settings.redis_decode_responses,
        socket_connect_timeout_seconds=settings.redis_socket_connect_timeout_seconds,
        socket_timeout_seconds=settings.redis_socket_timeout_seconds,
        read_from_slaves=settings.redis_read_from_slaves,
    )
    redis_client.ping()
    log.info(
        "Redis connected masters=%s slaves=%s prefix=%s.",
        len(redis_client.master_clients),
        len(redis_client.slave_clients),
        settings.redis_key_prefix,
    )
    return redis_client


def create_cache_store(settings: Settings, redis_client: Optional[StrictRedisClient]) -> CacheStore:
    if settings.local_mode or redis_client is None:
        log.info("Using local in-memory cache store.")
        return LocalCacheStore()
    log.info("Using Redis cache store.")
    return RedisCacheStore(redis_client)


def create_quran_components(
        settings: Settings,
        cache_store: CacheStore,
) -> tuple:
    if not settings.quran_api_configured:
        log.warning(
            "Quran API disabled - set QURAN_CLIENT_ID and QURAN_CLIENT_SECRET."
        )
        return None, None

    provider: TokenProvider = OAuthTokenProvider(settings)
    http_inner = HttpxClient(timeout=settings.request_timeout_seconds)
    if settings.cache_enabled:
        http_client: HttpClient = RedisCachingHttpClient(
            http_inner,
            cache_store,
            settings.api_get_cache_ttl_seconds,
            settings.redis_key_prefix,
        )
    else:
        http_client = http_inner
    client = QuranApiClient(settings, provider, http_client)
    oauth_service = QuranOAuthService(provider)
    return client, oauth_service


def create_masjid_search_service(
        settings: Settings,
        cache_store: CacheStore,
) -> MasjidSearchService:
    places_client = GooglePlacesClient(
        api_key=settings.google_places_api_key or "",
        timeout=settings.request_timeout_seconds,
    )
    inner = GoogleMasjidSearchService(places_client)
    if settings.cache_enabled:
        return CachedMasjidSearchService(
            inner,
            cache_store,
            settings.api_get_cache_ttl_seconds,
            settings.redis_key_prefix,
        )
    return inner


def create_user_repository(app: FastAPI, settings: Settings) -> UserRepository:
    if settings.mongodb_configured:
        if not settings.mongodb_uri or not str(settings.mongodb_uri).strip():
            raise RuntimeError(
                "MONGODB_URI is required when MONGODB_ENABLED (or MONGODB) is true."
            )
        client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=10_000,
        )
        try:
            client.admin.command("ping")
        except Exception as exc:
            client.close()
            raise RuntimeError(
                "MongoDB ping failed - check MONGODB_URI, credentials, and firewall "
                "(e.g. GCP allowlist for Atlas / self-hosted port 27017)."
            ) from exc
        app.state.mongo_client = client
        return MongoUserStore(client.get_database(settings.mongodb_database))

    app.state.mongo_client = None
    if settings.local_mode:
        return LocalCacheUserStore()

    redis_client = app.state.redis
    if redis_client is None:
        raise RuntimeError(
            "Redis must be reachable when LOCAL_MODE is false and MongoDB is off."
        )
    return RedisUserStore(redis_client, settings)


def create_phone_auth_service(
        settings: Settings,
        user_store: UserRepository,
        msg91_pending: Msg91PendingReqIdStore,
) -> PhoneAuthService:
    return PhoneAuthService(
        store=user_store,
        otp_gateway=Msg91OtpGateway(settings),
        phone_validator=IndiaPhoneValidator(settings.msg91_country_code),
        session_ttl_seconds=settings.auth_session_ttl_seconds,
        msg91_pending=msg91_pending,
        msg91_async_req_id_wait_seconds=settings.msg91_async_req_id_wait_seconds,
    )


def bootstrap(app: FastAPI, settings: Settings) -> None:
    app.state.settings = settings
    app.state.redis = create_redis_client(settings)
    app.state.cache_store = create_cache_store(settings, app.state.redis)

    msg91_pending = Msg91PendingReqIdStore(
        redis_client=app.state.redis,
        ttl_seconds=300.0,
        key_prefix=settings.redis_key_prefix,
    )
    app.state.msg91_pending_req_id_store = msg91_pending

    log.info(
        "MSG91 config loaded widget_id=%s country_code=%s auth_key=%s",
        settings.msg91_widget_id or "",
        settings.msg91_country_code,
        mask_secret((settings.msg91_auth_key or "").strip()),
    )

    quran_client, quran_oauth = create_quran_components(settings, app.state.cache_store)
    app.state.quran_api_client = quran_client
    app.state.quran_oauth_service = quran_oauth

    masjid_search = create_masjid_search_service(settings, app.state.cache_store)
    app.state.masjid_search_service = masjid_search

    user_store = create_user_repository(app, settings)
    app.state.user_store = user_store
    if isinstance(user_store, MongoUserStore):
        app.state.user_store_backend = "mongodb"
    elif isinstance(user_store, RedisUserStore):
        app.state.user_store_backend = "redis"
    else:
        app.state.user_store_backend = "local_cache"

    app.state.api_response_cache = settings.cache_enabled
    app.state.phone_auth_service = create_phone_auth_service(
        settings, user_store, msg91_pending,
    )
    if (
            settings.uvicorn_workers > 1
            and settings.msg91_async_req_id_wait_seconds > 0
            and app.state.redis is None
    ):
        log.warning(
            "MSG91 async requestId buffer uses process memory; multiple uvicorn workers "
            "may miss webhooks. Enable Redis or use a single worker."
        )

    app.state.user_masjid_service = UserMasjidService(
        store=user_store,
        places_reader=masjid_search,
    )

    log.info(
        "Bootstrap complete - persistence=%s - api_response_cache=%s - local_mode=%s.",
        app.state.user_store_backend,
        app.state.api_response_cache,
        settings.local_mode,
    )
