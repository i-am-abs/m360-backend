from typing import Optional

from core.auth.jwt_service import JwtService
from core.auth.mongo_user_repository import MongoUserRepository
from core.auth.user_repository import UserRepository
from core.config.app_config import AppConfig
from core.config.env_app_config import EnvAppConfig
from feature_flag.env_feature_flag_provider import EnvFeatureFlagProvider
from feature_flag.feature_flag_provider import FeatureFlagProvider
from masjid.masjid_repository import MasjidRepository
from masjid.masjid_service import MasjidService
from masjid.impl.mongo_masjid_repository import MongoMasjidRepository
from utils.logger import Logger

logger = Logger.get_logger(__name__)

_app_config: Optional[AppConfig] = None
_user_repository: Optional[UserRepository] = None
_jwt_service: Optional[JwtService] = None
_masjid_repository: Optional[MasjidRepository] = None
_masjid_service: Optional[MasjidService] = None
_feature_flag_provider: Optional[FeatureFlagProvider] = None


def get_app_config() -> AppConfig:
    global _app_config
    if _app_config is None:
        _app_config = EnvAppConfig()
    return _app_config


def get_user_repository() -> UserRepository:
    global _user_repository
    if _user_repository is None:
        config = get_app_config()
        _user_repository = MongoUserRepository(
            mongo_uri=config.get_mongo_uri(),
            db_name=config.get_mongo_db_name(),
        )
    return _user_repository


def get_jwt_service() -> JwtService:
    global _jwt_service
    if _jwt_service is None:
        config = get_app_config()
        _jwt_service = JwtService(
            secret_key=config.get_jwt_secret_key(),
            algorithm=config.get_jwt_algorithm(),
            expiration_minutes=config.get_jwt_expiration_minutes(),
        )
    return _jwt_service


def get_masjid_repository() -> MasjidRepository:
    global _masjid_repository
    if _masjid_repository is None:
        config = get_app_config()
        _masjid_repository = MongoMasjidRepository(
            mongo_uri=config.get_mongo_uri(),
            db_name=config.get_mongo_db_name(),
        )
    return _masjid_repository


def get_feature_flag_provider() -> FeatureFlagProvider:
    global _feature_flag_provider
    if _feature_flag_provider is None:
        _feature_flag_provider = EnvFeatureFlagProvider()
    return _feature_flag_provider


def get_masjid_service() -> MasjidService:
    global _masjid_service
    if _masjid_service is None:
        _masjid_service = MasjidService(
            repository=get_masjid_repository(),
            config=get_app_config(),
            feature_flag_provider=get_feature_flag_provider(),
        )
    return _masjid_service


def reset_container() -> None:
    global _app_config, _user_repository, _jwt_service, _masjid_repository, _masjid_service, _feature_flag_provider
    _app_config = None
    _user_repository = None
    _jwt_service = None
    _masjid_repository = None
    _masjid_service = None
    _feature_flag_provider = None
