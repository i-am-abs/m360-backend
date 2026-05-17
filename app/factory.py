from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.bootstrap import bootstrap
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.exceptions.handlers import register_exception_handlers
from app.middleware.api_get_response_cache import ApiGetResponseCacheMiddleware
from app.middleware.request_context import RequestContextMiddleware


@asynccontextmanager
async def application_lifespan(app: FastAPI):
    settings = app.state.settings
    log = get_logger(__name__)
    log.info("application_startup env=%s", settings.app_env)
    yield
    cache_store = getattr(app.state, "cache_store", None)
    if cache_store is not None:
        try:
            cache_store.close()
        except Exception:
            pass
        log.info("cache_store_closed")
    redis_client = getattr(app.state, "redis", None)
    if redis_client is not None:
        try:
            redis_client.close()
        except Exception:
            pass
        log.info("redis_client_closed")
    client = getattr(app.state, "mongo_client", None)
    if client is not None:
        client.close()
        log.info("mongodb_client_closed")
    log.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(
        level_name=settings.logging_level,
        logs_dir=settings.logs_dir,
    )

    application = FastAPI(
        title="Quran Foundation API Wrapper",
        version="1.0.0",
        description="FastAPI wrapper over Quran Foundation APIs with OAuth2 authentication",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=application_lifespan,
    )
    bootstrap(application, settings)
    application.add_middleware(RequestContextMiddleware)
    if settings.cache_enabled:
        application.add_middleware(
            ApiGetResponseCacheMiddleware,
            cache_store=application.state.cache_store,
            ttl_seconds=settings.api_get_cache_ttl_seconds,
            key_prefix=settings.redis_key_prefix,
            excluded_paths=settings.api_get_cache_excluded_paths,
        )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=list(settings.cors_allow_methods),
        allow_headers=list(settings.cors_allow_headers),
    )
    register_exception_handlers(application)
    application.include_router(api_v1_router)
    return application
