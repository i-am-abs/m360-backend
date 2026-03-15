from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.auth_routes import auth_router
from api.feature_flag_routes import feature_flag_router
from api.masjid_routes import masjid_router
from api.otp_routes import otp_router
from api.routes import router
from db.mongo_client import close_mongo_client, get_database
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
    try:
        db = get_database()
        db.command("ping")
        logger.info("MongoDB connection verified")
    except Exception as e:
        logger.warning("MongoDB not reachable at startup: %s (endpoints needing DB will fail)", e)
    yield
    close_mongo_client()
    logger.info("API Shutting Down...")


app = FastAPI(
    title="M360 Backend API",
    version="3.0.0",
    description="Backend API for M360 — Quran, Masjid, OTP, and Feature Flags",
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
app.include_router(otp_router)
app.include_router(feature_flag_router)
app.include_router(masjid_router)
app.include_router(router)

app.add_exception_handler(ApiException, api_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
