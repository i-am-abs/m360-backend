from abc import ABC, abstractmethod
from typing import Any, Dict, List


class MasjidRepository(ABC):
    @abstractmethod
    def find_nearby(
            self,
            longitude: float,
            latitude: float,
            radius_km: float,
            limit: int = 50,
    ) -> List[Dict[str, Any]]:
        pass
