from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import bootstrap
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.module_registry import attachEnabledModulesToAppState, buildApiV1Router, resolveModuleActivationState
from app.exceptions.handlers import register_exception_handlers
from app.middleware.normalize_path import NormalizePathMiddleware
from app.middleware.request_context import RequestContextMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    moduleActivationState = resolveModuleActivationState(settings)

    setup_logging(
        level_name=settings.logging_level,
        logs_dir=settings.logs_dir,
    )
    log = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info(
            "application_startup env=%s active_modules=%s",
            settings.app_env,
            ",".join(moduleActivationState.activeModuleNames()),
        )
        yield
        redisClient = getattr(app.state, "redis", None)
        if redisClient is not None:
            try:
                redisClient.close()
            except Exception:
                pass
            log.info("redis_client_closed")
        mongoClient = getattr(app.state, "mongo_client", None)
        if mongoClient is not None:
            mongoClient.close()
            log.info("mongodb_client_closed")
        log.info("application_shutdown")

    docsUrl = "/docs" if settings.api_docs_enabled else None
    redocUrl = "/redoc" if settings.api_docs_enabled else None

    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url=docsUrl,
        redoc_url=redocUrl,
        lifespan=lifespan,
    )
    bootstrap(application, settings)
    attachEnabledModulesToAppState(application, moduleActivationState)
    application.add_middleware(NormalizePathMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=list(settings.cors_allow_methods),
        allow_headers=list(settings.cors_allow_headers),
    )
    register_exception_handlers(application)
    apiV1Router = buildApiV1Router(moduleActivationState)
    application.include_router(apiV1Router, prefix="/api/v1")
    application.include_router(apiV1Router)
    return application
