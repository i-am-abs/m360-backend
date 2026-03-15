from abc import ABC, abstractmethod
from typing import Optional


class CityResolver(ABC):
    @abstractmethod
    def get_city(self, latitude: float, longitude: float) -> Optional[str]:
        pass
