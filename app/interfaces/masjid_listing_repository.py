from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MasjidListingRepository(ABC):
    @abstractmethod
    def get_listing(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Return listing metadata (admin status, tag, message)."""

    @abstractmethod
    def upsert_listing(self, place_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update listing metadata."""

    @abstractmethod
    def list_by_place_ids(self, place_ids: List[str]) -> List[Dict[str, Any]]:
        """Batch fetch listings for multiple place ids."""
