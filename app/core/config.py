from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

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

    quran_module_enabled: bool = Field(default=True, validation_alias=AliasChoices("QURAN_MODULE_ENABLED", "quran_module_enabled"))
    masjid_module_enabled: bool = Field(default=True, validation_alias=AliasChoices("MASJID_MODULE_ENABLED", "masjid_module_enabled"))
    auth_module_enabled: bool = Field(default=True, validation_alias=AliasChoices("AUTH_MODULE_ENABLED", "auth_module_enabled"))
    msg91_webhook_module_enabled: bool = Field(default=True, validation_alias=AliasChoices("MSG91_WEBHOOK_MODULE_ENABLED", "msg91_webhook_module_enabled"))
    feature_flag_module_enabled: bool = Field(default=True, validation_alias=AliasChoices("FEATURE_FLAG_MODULE_ENABLED", "feature_flag_module_enabled"))
    redis_cache_module_enabled: bool = Field(default=True, validation_alias=AliasChoices("REDIS_CACHE_MODULE_ENABLED", "redis_cache_module_enabled"))
    api_docs_enabled: bool = Field(default=True, validation_alias=AliasChoices("API_DOCS_ENABLED", "api_docs_enabled"))
    quran_base_url: str = "https://apis.quran.foundation"
    quran_client_id: Optional[str] = None
    quran_client_secret: Optional[str] = None
    quran_oauth_url: str = "https://oauth2.quran.foundation"
    jwt_expiration_minutes: int = 60
    google_places_api_key: Optional[str] = None
    masjid_search_radius_meters: int = 5000
    masjid_cache_ttl_seconds: int = Field(default=86_400, validation_alias=AliasChoices("MASJID_CACHE_TTL_SECONDS", "masjid_cache_ttl_seconds"))
    msg91_auth_key: Optional[str] = None
    msg91_widget_id: Optional[str] = None
    msg91_country_code: str = "91"
    msg91_async_req_id_wait_seconds: float = 3.0
    auth_session_ttl_seconds: int = Field(default=0, validation_alias=AliasChoices("AUTH_SESSION_TTL_SECONDS", "auth_session_ttl_seconds"))
    user_store_file: str = "data/user_store.json"
    mongodb_enabled: bool = Field(default=False, validation_alias=AliasChoices("MONGODB_ENABLED", "MONGODB", "mongodb_enabled"))
    mongodb_uri: Optional[str] = None
    mongodb_database: str = "m360"
    redis_enabled: bool = Field(default=False, validation_alias=AliasChoices("REDIS_ENABLED", "redis_enabled"))
    redis_url: Optional[str] = None
    redis_key_prefix: str = "m360"
    api_get_cache_ttl_seconds: int = 300
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
    def msg91_configured(self) -> bool:
        return bool(self.msg91_auth_key and self.msg91_widget_id)

    @property
    def google_places_configured(self) -> bool:
        return bool(self.google_places_api_key)

    @property
    def quran_module_active(self) -> bool:
        return self.quran_module_enabled and self.quran_api_configured

    @property
    def masjid_module_active(self) -> bool:
        return self.masjid_module_enabled and self.google_places_configured

    @property
    def auth_module_active(self) -> bool:
        return self.auth_module_enabled and self.msg91_configured

    @property
    def msg91_webhook_module_active(self) -> bool:
        return self.msg91_webhook_module_enabled and self.auth_module_active

    @property
    def feature_flag_module_active(self) -> bool:
        return self.feature_flag_module_enabled

    @property
    def redis_cache_module_active(self) -> bool:
        return self.redis_cache_module_enabled and self.redis_configured

    @property
    def mongodb_configured(self) -> bool:
        return self.mongodb_enabled and bool(self.mongodb_uri and self.mongodb_uri.strip())

    @property
    def redis_configured(self) -> bool:
        return self.redis_enabled and bool(self.redis_url and str(self.redis_url).strip())

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def auth_session_never_expires(self) -> bool:
        return self.auth_session_ttl_seconds <= 0

    @field_validator("quran_base_url", "quran_oauth_url", mode="before")
    @classmethod
    def stripTrailingSlash(cls, value: str) -> str:
        return value.strip().rstrip("/") if isinstance(value, str) else value

    @field_validator("auth_session_ttl_seconds", mode="before")
    @classmethod
    def normalizeSessionTtl(cls, value: object) -> int:
        if isinstance(value, bool):
            return 0
        try:
            if value is None:
                return 0
            ttlSeconds = int(str(value))
        except (TypeError, ValueError):
            return 0
        return max(0, ttlSeconds)

    @field_validator("masjid_search_radius_meters", mode="before")
    @classmethod
    def clampRadius(cls, value: int) -> int:
        try:
            radiusMeters = int(value)
        except (TypeError, ValueError):
            return 5000
        return max(500, min(50_000, radiusMeters))


def create_ssl_context() -> ssl.SSLContext:
    sslContext = ssl.create_default_context()
    try:
        sslContext.minimum_version = ssl.TLSVersion.TLSv1_2
    except AttributeError:
        pass
    return sslContext


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
