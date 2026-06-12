from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pymongo import MongoClient
from redis import Redis

from app.core.config import Settings
from app.core.logging import get_logger
from app.gateways.http_client import HttpxClient
from app.gateways.msg91_gateway import Msg91OtpGateway
from app.gateways.oauth_token_provider import OAuthTokenProvider
from app.gateways.redis_caching_http_client import RedisCachingHttpClient
from app.integrations.msg91_pending_req import Msg91PendingReqIdStore
from app.interfaces.http_client import HttpClient
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.token_provider import TokenProvider
from app.interfaces.user_repository import UserRepository
from app.repositories.google_places_client import GooglePlacesClient
from app.repositories.local_cache_user_store import LocalCacheUserStore
from app.repositories.mongo_masjid_store import MongoMasjidStore, NoOpMasjidStore
from app.repositories.mongo_user_store import MongoUserStore
from app.repositories.redis_user_store import RedisUserStore
from app.services.cached_masjid_search_service import CachedMasjidSearchService
from app.services.masjid_search_service import GoogleMasjidSearchService
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.user_masjid_service import UserMasjidService
from app.utils.phone import IndiaPhoneValidator

_log = get_logger(__name__)


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _init_redis(app: FastAPI, settings: Settings) -> None:
    app.state.redis = None
    if not settings.redis_configured:
        return
    r = Redis.from_url(
        settings.redis_url or "",
        decode_responses=True,
        socket_connect_timeout=5,
    )
    try:
        r.ping()
    except Exception as exc:
        _log.warning(
            "Redis unreachable at %s — continuing without Redis (%s). "
            "Set REDIS_ENABLED=false or start Redis to remove this warning.",
            settings.redis_url,
            exc,
        )
        return
    app.state.redis = r
    _log.info("Redis connected for caching and optional persistence (prefix=%s).", settings.redis_key_prefix)


def _create_quran_components(
        settings: Settings,
        redis_client: Optional[Redis],
) -> tuple:
    if not settings.quran_api_configured:
        _log.warning(
            "Quran API disabled — set QURAN_CLIENT_ID and QURAN_CLIENT_SECRET."
        )
        return None, None

    provider: TokenProvider = OAuthTokenProvider(settings)
    http_inner = HttpxClient(timeout=settings.request_timeout_seconds)
    if (
            redis_client is not None
            and settings.api_get_cache_ttl_seconds > 0
    ):
        http_client: HttpClient = RedisCachingHttpClient(
            http_inner,
            redis_client,
            settings.api_get_cache_ttl_seconds,
            settings.redis_key_prefix,
        )
    else:
        http_client = http_inner
    client = QuranApiClient(settings, provider, http_client)
    oauth_service = QuranOAuthService(provider)
    return client, oauth_service


def _create_masjid_search_service(
        settings: Settings,
        redis_client: Optional[Redis],
) -> MasjidSearchService:
    places_client = GooglePlacesClient(
        api_key=settings.google_places_api_key or "",
        timeout=settings.request_timeout_seconds,
    )
    inner = GoogleMasjidSearchService(places_client)
    if (
            redis_client is not None
            and settings.api_get_cache_ttl_seconds > 0
    ):
        return CachedMasjidSearchService(
            inner,
            redis_client,
            settings.api_get_cache_ttl_seconds,
            settings.redis_key_prefix,
        )
    return inner


def _create_masjid_store(
        settings: Settings,
        mongo_client: Optional[MongoClient],
) -> "MongoMasjidStore | NoOpMasjidStore":
    """Return a ``MongoMasjidStore`` when MongoDB is configured, else a no-op stub."""
    if settings.mongodb_configured and mongo_client is not None:
        return MongoMasjidStore(mongo_client.get_database(settings.mongodb_database))
    return NoOpMasjidStore()


def _create_user_repository(app: FastAPI, settings: Settings) -> UserRepository:
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
        except Exception as e:
            client.close()
            raise RuntimeError(
                "MongoDB ping failed — check MONGODB_URI, credentials, and firewall "
                "(e.g. GCP allowlist for Atlas / self-hosted port 27017)."
            ) from e
        app.state.mongo_client = client
        return MongoUserStore(client.get_database(settings.mongodb_database))
    app.state.mongo_client = None
    if settings.redis_configured and app.state.redis is not None:
        return RedisUserStore(app.state.redis, settings)
    if settings.redis_configured:
        _log.warning(
            "REDIS_ENABLED is true but Redis is unavailable — using JSON file user store."
        )
    if settings.user_store_file:
        from app.repositories.user_store import JsonFileUserStore
        return JsonFileUserStore(settings.user_store_file)
    return LocalCacheUserStore()


def _create_phone_auth_service(
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
    _init_redis(app, settings)

    msg91_pending = Msg91PendingReqIdStore(
        redis_client=app.state.redis,
        ttl_seconds=300.0,
        key_prefix=settings.redis_key_prefix,
    )
    app.state.msg91_pending_req_id_store = msg91_pending

    _log.info(
        "MSG91 config loaded widget_id=%s country_code=%s auth_key=%s",
        settings.msg91_widget_id or "",
        settings.msg91_country_code,
        _mask_secret((settings.msg91_auth_key or "").strip()),
    )

    quran_client, quran_oauth = _create_quran_components(settings, app.state.redis)
    app.state.quran_api_client = quran_client
    app.state.quran_oauth_service = quran_oauth

    masjid_search = _create_masjid_search_service(settings, app.state.redis)
    app.state.masjid_search_service = masjid_search

    user_store = _create_user_repository(app, settings)
    app.state.user_store = user_store
    if isinstance(user_store, MongoUserStore):
        app.state.user_store_backend = "mongodb"
    elif isinstance(user_store, RedisUserStore):
        app.state.user_store_backend = "redis"
    else:
        app.state.user_store_backend = "local_cache"
    app.state.api_response_cache = (
            app.state.redis is not None and settings.api_get_cache_ttl_seconds > 0
    )

    app.state.phone_auth_service = _create_phone_auth_service(
        settings, user_store, msg91_pending,
    )
    if (
            settings.uvicorn_workers > 1
            and settings.msg91_async_req_id_wait_seconds > 0
            and app.state.redis is None
    ):
        _log.warning(
            "MSG91 async requestId buffer uses process memory; multiple uvicorn workers "
            "may miss webhooks. Enable Redis or use a single worker."
        )

    app.state.user_masjid_service = UserMasjidService(
        store=user_store,
        places_reader=masjid_search,
    )

    # Masjid committee / amenities store (MongoDB when available, no-op otherwise)
    app.state.masjid_store = _create_masjid_store(
        settings, app.state.mongo_client
    )

    mode = app.state.user_store_backend
    _log.info(
        "Bootstrap complete — persistence=%s — api_response_cache=%s — "
        "auth_session_ttl_seconds=%s (never_expires=%s) — all services wired.",
        mode,
        app.state.api_response_cache,
        settings.auth_session_ttl_seconds,
        settings.auth_session_never_expires,
    )
