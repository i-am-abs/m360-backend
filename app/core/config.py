from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent


def _bootstrap_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = PROJECT_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


_bootstrap_dotenv()


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

    auth_session_ttl_seconds: int = Field(
        default=0,
        description="Phone login bearer TTL in seconds. 0 = never expires.",
        validation_alias=AliasChoices(
            "AUTH_SESSION_TTL_SECONDS",
            "auth_session_ttl_seconds",
        ),
    )

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

    redis_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("REDIS_ENABLED", "redis_enabled"),
    )
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

    internal_api_key: Optional[str] = None
    internal_timings_cache_ttl_seconds: int = 60

    r2_endpoint_url: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_public_base_url: Optional[str] = None

    mux_token_id: Optional[str] = None
    mux_token_secret: Optional[str] = None

    upload_max_image_bytes: int = 10 * 1024 * 1024
    upload_max_video_bytes: int = 200 * 1024 * 1024

    rate_limit_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("RATE_LIMIT_ENABLED", "rate_limit_enabled"),
    )
    rate_limit_requests_per_minute: int = Field(default=120, ge=1)
    rate_limit_auth_requests_per_minute: int = Field(default=20, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    auth_force_infinite_sessions: bool = Field(
        default=True,
        description="When true, bearer tokens never expire for user, admin, and super_admin.",
        validation_alias=AliasChoices(
            "AUTH_FORCE_INFINITE_SESSIONS",
            "auth_force_infinite_sessions",
        ),
    )

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
        return self.redis_enabled and bool(self.redis_url and str(self.redis_url).strip())

    @property
    def r2_configured(self) -> bool:
        return bool(
            self.r2_endpoint_url
            and self.r2_bucket_name
            and self.r2_access_key_id
            and self.r2_secret_access_key
        )

    @property
    def mux_configured(self) -> bool:
        return bool(self.mux_token_id and self.mux_token_secret)

    @property
    def internal_api_configured(self) -> bool:
        return bool(self.internal_api_key and self.internal_api_key.strip())

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @field_validator("quran_base_url", "quran_oauth_url", mode="before")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.strip().rstrip("/") if isinstance(v, str) else v

    @field_validator("auth_session_ttl_seconds", mode="before")
    @classmethod
    def _normalize_session_ttl(cls, v: object) -> int:
        try:
            ttl = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0
        return max(0, ttl)

    @property
    def auth_session_never_expires(self) -> bool:
        if self.auth_force_infinite_sessions:
            return True
        return self.auth_session_ttl_seconds <= 0

    @property
    def effective_session_ttl_seconds(self) -> int:
        if self.auth_force_infinite_sessions:
            return 0
        return self.auth_session_ttl_seconds

    @field_validator("masjid_search_radius_meters", mode="before")
    @classmethod
    def _clamp_radius(cls, v: int) -> int:
        try:
            v = int(v)
        except (TypeError, ValueError):
            return 5000
        return max(500, min(50_000, v))


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
