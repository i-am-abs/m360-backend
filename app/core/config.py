from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from pydantic import AliasChoices, Field, SecretStr, field_validator
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

    secret_key: SecretStr = Field(
        default="change-me-in-production",
        description="JWT signing secret for admin panel tokens.",
        validation_alias=AliasChoices("SECRET_KEY", "secret_key"),
    )

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

    # Payment Gateway (Razorpay)
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None

    # Donation default
    donation_cache_ttl_seconds: int = 60

    # Platform admin
    platform_admin_env: str = ""

    # Admin panel (web UI)
    super_admins: Optional[str] = None
    admin_panel_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ADMIN_PANEL_ENABLED",
            "admin_panel_enabled",
        ),
    )
    admin_session_ttl_seconds: int = Field(
        default=86400,
        description="Admin session TTL in seconds (default 24h).",
        validation_alias=AliasChoices(
            "ADMIN_SESSION_TTL_SECONDS",
            "admin_session_ttl_seconds",
        ),
    )

    # FCM Push Notifications
    fcm_service_account_path: str = ""

    # Mux Video
    mux_token_id: str = ""
    mux_token_secret: str = ""
    mux_webhook_secret: str = ""
    mux_env_key: str = "deb2jrkrr735ufr00gdtrf8j9"

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
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def payment_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

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
        return self.auth_session_ttl_seconds <= 0

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
