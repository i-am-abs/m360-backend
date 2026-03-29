from typing import Final, Tuple


class AppSettings:
    TITLE: Final[str] = "Quran Foundation API Wrapper"
    VERSION: Final[str] = "1.0.0"
    DESCRIPTION: Final[str] = (
        "FastAPI wrapper over Quran Foundation APIs with OAuth2 authentication"
    )
    DOCS_URL: Final[str] = "/docs"
    REDOC_URL: Final[str] = "/redoc"

    UVICORN_HOST: Final[str] = "0.0.0.0"
    UVICORN_PORT: Final[int] = 8000
    UVICORN_RELOAD_LOG_LEVEL: Final[str] = "debug"

    CORS_ALLOW_ORIGINS: Final[Tuple[str, ...]] = ("*",)
    CORS_ALLOW_CREDENTIALS: Final[bool] = True
    CORS_ALLOW_METHODS: Final[Tuple[str, ...]] = ("*",)
    CORS_ALLOW_HEADERS: Final[Tuple[str, ...]] = ("*",)
