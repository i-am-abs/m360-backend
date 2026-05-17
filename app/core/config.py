from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent


def bootstrap_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = PROJECT_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


bootstrap_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "prod"
    app_name: str = "m360.quran.api"
    server_port: int = 8000
    logging_level: str = "INFO"
    logs_dir: str = "logs"

    quran_base_url: str = "https://apis.quran.foundation"
    quran_client_id: Optional[str] = None
    quran_client_secret: Optional[str] = None
    quran_oauth_url: str = "https://oauth2.quran.foundation"

    jwt_expiration_minutes: int = 60

    google_places_api_key: Optional[str] = None
    masjid_search_radius_meters: int = 5000

    msg91_auth_key: Optional[str] = None

    msg91_widget_id: Optional[str] = None
    msg91_country_code: str = "91"
    msg91_async_req_id_wait_seconds: float = 3.0

    auth_session_ttl_seconds: int = 86400

    user_store_file: str = "data/user_store.json"

    mongodb_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "MONGODB_ENABLED",
            "MONGODB",
            "mongodb_enabled",
        ),
    )
    mongodb_uri: Optional[str] = None
    mongodb_database: str = "m360"

    local_mode: bool = Field(
        default=True,
        validation_alias=AliasChoices("LOCAL_MODE", "local_mode"),
    )
    redis_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("REDIS_ENABLED", "redis_enabled"),
    )
    redis_url: Optional[str] = None
    redis_master_urls: Tuple[str, ...] = Field(
        default=(
            "redis://localhost:6379/0",
            "redis://localhost:6380/0",
            "redis://localhost:6381/0",
        ),
        validation_alias=AliasChoices("REDIS_MASTER_URLS", "redis_master_urls"),
    )
    redis_slave_urls: Tuple[str, ...] = Field(
        default=(
            "redis://localhost:6382/0",
            "redis://localhost:6383/0",
            "redis://localhost:6384/0",
        ),
        validation_alias=AliasChoices("REDIS_SLAVE_URLS", "redis_slave_urls"),
    )
    redis_key_prefix: str = "m360"
    redis_decode_responses: bool = True
    redis_socket_connect_timeout_seconds: float = 5.0
    redis_socket_timeout_seconds: float = 5.0
    redis_read_from_slaves: bool = False
    api_get_cache_ttl_seconds: int = 300
    api_get_cache_excluded_paths: Tuple[str, ...] = (
        "/health",
        "/health/live",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    )

    uvicorn_workers: int = 2
    forwarded_allow_ips: str = "*"

    request_timeout_seconds: int = 10

    cors_allow_origins: Tuple[str, ...] = ("*",)
    cors_allow_credentials: bool = True
    cors_allow_methods: Tuple[str, ...] = ("*",)
    cors_allow_headers: Tuple[str, ...] = ("*",)

    @property
    def quran_api_configured(self) -> bool:
        return bool(self.quran_client_id and self.quran_client_secret)

    @property
    def masjid_module_enabled(self) -> bool:
        return bool(self.google_places_api_key)

    @property
    def mongodb_configured(self) -> bool:
        return self.mongodb_enabled and bool(self.mongodb_uri and self.mongodb_uri.strip())

    @property
    def redis_configured(self) -> bool:
        return not self.local_mode and bool(self.redis_master_urls)

    @property
    def cache_enabled(self) -> bool:
        return self.api_get_cache_ttl_seconds > 0

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @field_validator("quran_base_url", "quran_oauth_url", mode="before")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.strip().rstrip("/") if isinstance(v, str) else v

    @field_validator("masjid_search_radius_meters", mode="before")
    @classmethod
    def clamp_radius(cls, v: int) -> int:
        try:
            v = int(v)
        except (TypeError, ValueError):
            return 5000
        return max(500, min(50_000, v))

    @field_validator(
        "cors_allow_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        "redis_master_urls",
        "redis_slave_urls",
        "api_get_cache_excluded_paths",
        mode="before",
    )
    @classmethod
    def parse_csv_tuple(cls, v):
        if isinstance(v, str):
            return tuple(item.strip() for item in v.split(",") if item.strip())
        return v


def create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    except AttributeError:
        pass
    return ctx


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
