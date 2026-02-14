from abc import ABC, abstractmethod


class AppConfig(ABC):
    @abstractmethod
    def get_mongo_uri(self) -> str:
        pass

    @abstractmethod
    def get_mongo_db_name(self) -> str:
        pass

    @abstractmethod
    def get_jwt_secret_key(self) -> str:
        pass

    @abstractmethod
    def get_jwt_algorithm(self) -> str:
        pass

    @abstractmethod
    def get_jwt_expiration_minutes(self) -> int:
        pass

    @abstractmethod
    def get_masjid_search_radius_km(self) -> float:
        pass
