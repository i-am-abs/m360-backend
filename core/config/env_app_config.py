import os

from core.config.app_config import AppConfig


class EnvAppConfig(AppConfig):
    def __init__(self) -> None:
        self._mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self._mongo_db = os.getenv("MONGO_DB_NAME", "m360")
        self._jwt_secret = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
        self._jwt_algo = os.getenv("JWT_ALGORITHM", "HS256")
        self._jwt_exp_min = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
        self._masjid_radius = float(os.getenv("MASJID_SEARCH_RADIUS_KM", "10"))
        self._google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()

    def get_mongo_uri(self) -> str:
        return self._mongo_uri

    def get_mongo_db_name(self) -> str:
        return self._mongo_db

    def get_jwt_secret_key(self) -> str:
        return self._jwt_secret

    def get_jwt_algorithm(self) -> str:
        return self._jwt_algo

    def get_jwt_expiration_minutes(self) -> int:
        return self._jwt_exp_min

    def get_masjid_search_radius_km(self) -> float:
        return self._masjid_radius

    def get_google_places_api_key(self) -> str:
        return self._google_places_api_key
