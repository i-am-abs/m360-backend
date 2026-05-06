from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.bootstrap import bootstrap
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.exceptions.handlers import register_exception_handlers
from app.middleware.request_context import RequestContextMiddleware


def create_app() -> FastAPI:
    settings = get_settings()

    setup_logging(
        level_name=settings.logging_level,
        logs_dir=settings.logs_dir,
    )
    log = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("application_startup env=%s", settings.app_env)
        yield
        log.info("application_shutdown")

    application = FastAPI(
        title="Quran Foundation API Wrapper",
        version="1.0.0",
        description="FastAPI wrapper over Quran Foundation APIs with OAuth2 authentication",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    bootstrap(application, settings)
    application.add_middleware(RequestContextMiddleware)
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
