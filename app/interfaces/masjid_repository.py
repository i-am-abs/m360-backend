from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MasjidRepository(ABC):
    @abstractmethod
    def get_committee(self, place_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def upsert_committee(
            self,
            place_id: str,
            data: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_timings(self, place_id: str) -> Optional[List[Dict[str, Any]]]:
        pass

    @abstractmethod
    def get_amenities(self, place_id: str) -> Optional[List[str]]:
        pass

    @abstractmethod
    def update_timings(
            self,
            place_id: str,
            timings: List[Dict[str, Any]],
            *,
            updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_amenities(
            self,
            place_id: str,
            amenities: List[str],
            *,
            updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass
