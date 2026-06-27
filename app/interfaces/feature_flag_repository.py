from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class FeatureFlagRepository(ABC):
    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_by_location_key(self, location_key: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_by_coordinates(
            self,
            latitude: float,
            longitude: float,
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_by_region(
            self,
            country: Optional[str],
            state: Optional[str],
            city: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        pass
