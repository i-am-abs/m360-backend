from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import Logger
from api.routes import router
from api.auth_routes import auth_router
from api.masjid_routes import masjid_router
from exceptions.api_exception import ApiException
from exceptions.impl.api_exception_handler import (
    api_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)

logger = Logger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API Starting...")
    yield
    logger.info("API Shutting Down...")


app = FastAPI(
    title="Quran Foundation API Wrapper",
    version="2.0.0",
    description="FastAPI wrapper over Quran Foundation APIs with OAuth2 authentication",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(masjid_router)
app.include_router(router)
app.add_exception_handler(ApiException, api_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
