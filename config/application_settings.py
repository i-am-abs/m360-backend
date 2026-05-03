from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from config.env_config import ENV, load_app_env
from config.factory.quran_config_factory import create_quran_api_config
from config.quran_api_config import QuranApiConfig
from constants.env_keys import EnvKeys
from constants.masjid_query import MasjidQueryLimits


@dataclass(frozen=True)
class MasjidModuleSettings:
    google_places_api_key: Optional[str]
    default_search_radius_meters: int

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> MasjidModuleSettings:
        raw_key = (env.get(EnvKeys.GOOGLE_PLACES_API_KEY.value) or "").strip()
        key = raw_key or None
        raw_radius = (
                env.get(EnvKeys.MASJID_SEARCH_RADIUS_METERS.value)
                or str(MasjidQueryLimits.SEARCH_RADIUS_DEFAULT_FALLBACK_M)
        ).strip()
        try:
            radius = int(raw_radius)
        except ValueError:
            radius = MasjidQueryLimits.SEARCH_RADIUS_DEFAULT_FALLBACK_M
        radius = max(
            MasjidQueryLimits.SEARCH_RADIUS_MIN_M,
            min(MasjidQueryLimits.SEARCH_RADIUS_MAX_M, radius),
        )
        return cls(
            google_places_api_key=key,
            default_search_radius_meters=radius,
        )

    def is_module_enabled(self) -> bool:
        return bool(self.google_places_api_key)


@dataclass(frozen=True)
class Msg91Settings:
    auth_key: str
    widget_id: str
    country_code: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Msg91Settings:
        return cls(
            auth_key=(env.get(EnvKeys.MSG91_AUTH_KEY.value) or "").strip(),
            widget_id=(env.get(EnvKeys.MSG91_WIDGET_ID.value) or "").strip(),
            country_code=(env.get(EnvKeys.MSG91_COUNTRY_CODE.value) or "").strip(),
        )


@dataclass(frozen=True)
class PhoneAuthSettings:
    session_ttl_seconds_raw: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> PhoneAuthSettings:
        return cls(
            session_ttl_seconds_raw=(
                    env.get(EnvKeys.AUTH_SESSION_TTL_SECONDS.value) or ""
            ).strip(),
        )


@dataclass(frozen=True)
class PersistenceSettings:
    user_store_file: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> PersistenceSettings:
        raw = (
            env.get(EnvKeys.USER_STORE_FILE.value) or "data/user_store.json"
        ).strip()
        return cls(user_store_file=raw or "data/user_store.json")


@dataclass(frozen=True)
class LoggingSettings:
    logs_dir: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> LoggingSettings:
        raw = (env.get(EnvKeys.LOGS_DIR.value) or "logs").strip()
        return cls(logs_dir=raw or "logs")


@dataclass(frozen=True)
class ApplicationSettings:
    quran_config: QuranApiConfig | None
    masjid: MasjidModuleSettings
    msg91: Msg91Settings
    phone_auth: PhoneAuthSettings
    persistence: PersistenceSettings
    logging: LoggingSettings

    @classmethod
    def build(cls) -> ApplicationSettings:
        load_app_env()
        env = ENV
        try:
            quran_config = create_quran_api_config(env)
        except ValueError:
            quran_config = None
        return cls(
            quran_config=quran_config,
            masjid=MasjidModuleSettings.from_env(env),
            msg91=Msg91Settings.from_env(env),
            phone_auth=PhoneAuthSettings.from_env(env),
            persistence=PersistenceSettings.from_env(env),
            logging=LoggingSettings.from_env(env),
        )
