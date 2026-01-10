from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import Logger
from api.routes import router
from api.auth_routes import auth_router
from exceptions.api_exception import ApiException
from exceptions.impl.api_exception_handler import api_exception_handler

logger = Logger.get_logger(__name__)

app = FastAPI(
    title="Quran Foundation API Wrapper",
    version="2.0.0",
    description="FastAPI wrapper over Quran Foundation APIs with OAuth2 authentication",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(router)
app.add_exception_handler(ApiException, api_exception_handler)


@app.on_event("startup")
async def startup_event():
    logger.info("API Starting...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API Shutting Down...")
