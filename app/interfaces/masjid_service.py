from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class PlacesReader(ABC):
    @abstractmethod
    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        pass


class MasjidSearchService(PlacesReader):
    @abstractmethod
    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def search_by_name(
            self,
            query: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def search_by_city(
            self,
            city: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        pass
