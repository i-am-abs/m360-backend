from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pymongo import MongoClient
from redis import StrictRedis

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.module_registry import ModuleActivationState, resolveModuleActivationState
from app.gateways.http_client import HttpxClient
from app.gateways.oauth_token_provider import OAuthTokenProvider
from app.gateways.redis_caching_http_client import RedisCachingHttpClient
from app.interfaces.http_client import HttpClient
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.token_provider import TokenProvider
from app.interfaces.user_repository import UserRepository
from app.modules.feature_flag.application.services.feature_flag_management_service import FeatureFlagManagementService
from app.modules.feature_flag.infrastructure.adapters.location_based_feature_flag_adapter import \
    LocationBasedFeatureFlagAdapter
from app.modules.feature_flag.infrastructure.configuration.feature_flag_module_configuration import \
    FeatureFlagModuleConfiguration
from app.modules.feature_flag.infrastructure.factories.feature_flag_evaluation_strategy_factory import \
    FeatureFlagEvaluationStrategyFactory
from app.modules.feature_flag.infrastructure.repositories.in_memory_feature_flag_repository import \
    InMemoryFeatureFlagRepository
from app.modules.masjid.configuration.masjid_module_configuration import MasjidModuleConfiguration
from app.modules.otp.configuration.otp_module_configuration import OtpModuleConfiguration
from app.modules.quran.configuration.quran_module_configuration import QuranModuleConfiguration
from app.repositories.google_places_client import GooglePlacesClient
from app.repositories.local_cache_user_store import InMemoryUserRepository
from app.repositories.mongo_user_store import MongoUserStore
from app.repositories.redis_user_store import RedisUserStore
from app.services.cached_masjid_search_service import CachedMasjidSearchService
from app.services.masjid_search_service import GoogleMasjidSearchService
from app.services.persisting_masjid_search_service import PersistingMasjidSearchService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService

logger = get_logger(__name__)


def initializeDefaultAppState(app: FastAPI, settings: Settings) -> None:
    app.state.settings = settings
    app.state.redis = None
    app.state.mongo_client = None
    app.state.user_store = None
    app.state.user_store_backend = "disabled"
    app.state.masjid_repository = None
    app.state.masjid_search_service = None
    app.state.user_masjid_service = None
    app.state.phone_auth_service = None
    app.state.quran_api_client = None
    app.state.quran_oauth_service = None
    app.state.feature_flag_management_service = None
    app.state.location_based_feature_flag_service = None
    app.state.msg91_pending_req_id_store = None
    app.state.api_response_cache = False


def initializeRedisIfEnabled(app: FastAPI, settings: Settings) -> None:
    if not settings.redis_configured:
        return
    redisClient = StrictRedis.from_url(
        settings.redis_url or "",
        decode_responses=True,
        socket_connect_timeout=5,
    )
    try:
        redisClient.ping()
    except Exception as exc:
        logger.warning(
            "Redis unreachable at %s — continuing without Redis (%s). "
            "Set REDIS_ENABLED=false or start Redis to remove this warning.",
            settings.redis_url,
            exc,
        )
        return
    app.state.redis = redisClient


def createUserRepository(app: FastAPI, settings: Settings) -> UserRepository:
    if settings.mongodb_configured:
        if not settings.mongodb_uri or not str(settings.mongodb_uri).strip():
            raise RuntimeError(
                "MONGODB_URI is required when MONGODB_ENABLED is true."
            )
        mongoClient = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=10_000,
        )
        try:
            mongoClient.admin.command("ping")
        except Exception as exc:
            mongoClient.close()
            raise RuntimeError(
                "MongoDB ping failed — check MONGODB_URI, credentials, and network access."
            ) from exc
        app.state.mongo_client = mongoClient
        return MongoUserStore(mongoClient.get_database(settings.mongodb_database))

    app.state.mongo_client = None
    if settings.redis_configured and app.state.redis is not None:
        return RedisUserStore(app.state.redis, settings)
    if settings.redis_configured:
        logger.warning(
            "REDIS_ENABLED is true but Redis is unavailable — using JSON file user repository."
        )
    if settings.user_store_file:
        from app.repositories.user_store import JsonFileUserRepository
        return JsonFileUserRepository(settings.user_store_file)
    return InMemoryUserRepository()


def createMasjidSearchService(settings: Settings, redisClient: Optional[Redis],
                              masjidRepository: Optional[MasjidRepository],
                              moduleActivationState: ModuleActivationState) -> MasjidSearchService:
    placesClient = GooglePlacesClient(
        api_key=settings.google_places_api_key or "",
        timeout=settings.request_timeout_seconds,
    )

    innerMasjidSearchService = GoogleMasjidSearchService(placesClient)
    if moduleActivationState.redisCacheModuleActive and redisClient is not None and settings.api_get_cache_ttl_seconds > 0:
        innerMasjidSearchService = CachedMasjidSearchService(
            innerMasjidSearchService,
            redisClient,
            settings.api_get_cache_ttl_seconds,
            settings.redis_key_prefix,
        )
    if masjidRepository is not None:
        return PersistingMasjidSearchService(
            innerMasjidSearchService=innerMasjidSearchService,
            masjidRepository=masjidRepository,
            masjidCacheTtlSeconds=settings.masjid_cache_ttl_seconds,
        )
    return innerMasjidSearchService


def createQuranComponents(settings: Settings, redisClient: Optional[Redis],
                          moduleActivationState: ModuleActivationState) -> tuple:
    provider: TokenProvider = OAuthTokenProvider(settings)
    httpInnerClient = HttpxClient(timeout=settings.request_timeout_seconds)
    if moduleActivationState.redisCacheModuleActive and redisClient is not None and settings.api_get_cache_ttl_seconds > 0:
        httpClient: HttpClient = RedisCachingHttpClient(
            httpInnerClient,
            redisClient,
            settings.api_get_cache_ttl_seconds,
            settings.redis_key_prefix,
        )
    else:
        httpClient = httpInnerClient
    quranApiClient = QuranApiClient(settings, provider, httpClient)
    quranOAuthService = QuranOAuthService(provider)
    return quranApiClient, quranOAuthService


def createDisabledLocationFeatureFlagAdapter() -> LocationBasedFeatureFlagAdapter:
    disabledFeatureFlagService = FeatureFlagManagementService(
        featureFlagRepository=InMemoryFeatureFlagRepository(),
        evaluationStrategyFactory=FeatureFlagEvaluationStrategyFactory(),
        runtimeEnvironmentName="disabled",
    )
    return LocationBasedFeatureFlagAdapter(disabledFeatureFlagService)


def bootstrapUserPersistenceModule(app: FastAPI, settings: Settings, moduleActivationState: ModuleActivationState) -> \
Optional[UserRepository]:
    if not moduleActivationState.userPersistenceModuleActive:
        return None
    userRepository = createUserRepository(app, settings)
    app.state.user_store = userRepository
    if isinstance(userRepository, MongoUserStore):
        app.state.user_store_backend = "mongodb"
    elif isinstance(userRepository, RedisUserStore):
        app.state.user_store_backend = "redis"
    else:
        app.state.user_store_backend = "local_cache"
    return userRepository


def bootstrapAuthModule(app: FastAPI, settings: Settings, userRepository: Optional[UserRepository],
                        moduleActivationState: ModuleActivationState) -> None:
    if not moduleActivationState.authModuleActive:
        return
    if userRepository is None:
        raise RuntimeError("Auth module requires user persistence to be enabled.")
    otpModuleFacade = OtpModuleConfiguration(
        settings=settings,
        redisClient=app.state.redis,
        userRepository=userRepository,
    ).createFacade()
    app.state.msg91_pending_req_id_store = otpModuleFacade.msg91PendingReqIdStore
    app.state.phone_auth_service = otpModuleFacade.phoneAuthService
    if settings.uvicorn_workers > 1 and settings.msg91_async_req_id_wait_seconds > 0 and app.state.redis is None:
        logger.warning(
            "MSG91 async requestId buffer uses process memory; multiple uvicorn workers may miss webhooks. Enable Redis or use a single worker.")


def bootstrapQuranModule(app: FastAPI, settings: Settings, moduleActivationState: ModuleActivationState) -> None:
    if not moduleActivationState.quranModuleActive:
        return
    quranModuleFacade = QuranModuleConfiguration(
        settings,
        app.state.redis,
        moduleActivationState.redisCacheModuleActive,
    ).createFacade()
    app.state.quran_api_client = quranModuleFacade.quranApiClient
    app.state.quran_oauth_service = quranModuleFacade.quranOAuthService


def bootstrapFeatureFlagModule(app: FastAPI, settings: Settings,
                               moduleActivationState: ModuleActivationState) -> LocationBasedFeatureFlagAdapter:
    if not moduleActivationState.featureFlagModuleActive:
        return createDisabledLocationFeatureFlagAdapter()
    mongoDatabase = None
    if app.state.mongo_client is not None:
        mongoDatabase = app.state.mongo_client.get_database(settings.mongodb_database)
    featureFlagModuleConfiguration = FeatureFlagModuleConfiguration(
        settings=settings,
        mongoDatabase=mongoDatabase,
    )
    featureFlagManagementService = featureFlagModuleConfiguration.createFeatureFlagManagementService()
    locationBasedFeatureFlagAdapter = featureFlagModuleConfiguration.createLocationBasedFeatureFlagAdapter(
        featureFlagManagementService
    )
    app.state.feature_flag_management_service = featureFlagManagementService
    app.state.location_based_feature_flag_service = locationBasedFeatureFlagAdapter
    return locationBasedFeatureFlagAdapter


def bootstrapMasjidModule(app: FastAPI, settings: Settings, userRepository: Optional[UserRepository],
                          locationBasedFeatureFlagAdapter: LocationBasedFeatureFlagAdapter,
                          moduleActivationState: ModuleActivationState) -> None:
    if not moduleActivationState.masjidModuleActive:
        return
    if userRepository is None:
        raise RuntimeError("Masjid module requires user persistence to be enabled.")
    masjidModuleFacade = MasjidModuleConfiguration(
        settings,
        app.state.redis,
        app.state.mongo_client,
        userRepository,
        locationBasedFeatureFlagAdapter,
        moduleActivationState.redisCacheModuleActive,
    ).createFacade()
    app.state.masjid_repository = masjidModuleFacade.masjidRepository
    app.state.masjid_search_service = masjidModuleFacade.masjidSearchService
    app.state.user_masjid_service = masjidModuleFacade.userMasjidService


def bootstrap(app: FastAPI, settings: Settings) -> None:
    moduleActivationState = resolveModuleActivationState(settings)
    initializeDefaultAppState(app, settings)
    initializeRedisIfEnabled(app, settings)
    app.state.api_response_cache = (
            moduleActivationState.redisCacheModuleActive
            and app.state.redis is not None
            and settings.api_get_cache_ttl_seconds > 0
    )

    userRepository = bootstrapUserPersistenceModule(app, settings, moduleActivationState)
    bootstrapAuthModule(app, settings, userRepository, moduleActivationState)
    bootstrapQuranModule(app, settings, moduleActivationState)
    locationBasedFeatureFlagAdapter = bootstrapFeatureFlagModule(app, settings, moduleActivationState)
    bootstrapMasjidModule(
        app,
        settings,
        userRepository,
        locationBasedFeatureFlagAdapter,
        moduleActivationState,
    )

    logger.info(
        "bootstrap_complete persistence=%s modules=%s cache=%s",
        app.state.user_store_backend,
        ",".join(moduleActivationState.activeModuleNames()),
        app.state.api_response_cache,
    )
