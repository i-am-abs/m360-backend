from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
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
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @field_validator("quran_base_url", "quran_oauth_url", mode="before")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.strip().rstrip("/") if isinstance(v, str) else v

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
