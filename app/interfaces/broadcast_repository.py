from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BroadcastRepository(ABC):
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a broadcast message and return the stored document."""

    @abstractmethod
    def list_by_masjid(
        self,
        masjid_id: str,
        *,
        limit: int,
        before_seq: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Return (items, has_more) reverse-sorted by ``seq`` (newest first).

        ``before_seq`` is a cursor: only items with ``seq`` < before_seq are
        returned, enabling "load older" pagination by last message id.
        """

    @abstractmethod
    def get_by_id(self, broadcast_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single broadcast by id."""
