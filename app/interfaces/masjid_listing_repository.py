from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MasjidListingRepository(ABC):
    @abstractmethod
    def get_listing(self, place_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def upsert_listing(self, place_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_by_place_ids(self, place_ids: List[str]) -> List[Dict[str, Any]]:
        pass
