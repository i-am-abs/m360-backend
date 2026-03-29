from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.auth_routes import auth_router
from api.masjid_routes import masjid_router
from api.quran_routes import quran_router
from constants.app_settings import AppSettings
from exceptions.api_exception import ApiException
from exceptions.impl.api_exception_handler import (
    api_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)
from logger.Logger import Logger

logger = Logger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API Starting...")
    yield
    logger.info("API Shutting Down...")


app = FastAPI(
    title=AppSettings.TITLE,
    version=AppSettings.VERSION,
    description=AppSettings.DESCRIPTION,
    docs_url=AppSettings.DOCS_URL,
    redoc_url=AppSettings.REDOC_URL,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(AppSettings.CORS_ALLOW_ORIGINS),
    allow_credentials=AppSettings.CORS_ALLOW_CREDENTIALS,
    allow_methods=list(AppSettings.CORS_ALLOW_METHODS),
    allow_headers=list(AppSettings.CORS_ALLOW_HEADERS),
)
app.include_router(auth_router)
app.include_router(quran_router)
app.include_router(masjid_router)
app.add_exception_handler(ApiException, api_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "main:app",
#         host=AppSettings.UVICORN_HOST,
#         port=AppSettings.UVICORN_PORT,
#         reload=True,
#         log_level=AppSettings.UVICORN_RELOAD_LOG_LEVEL,
#     )
