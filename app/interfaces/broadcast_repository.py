from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BroadcastRepository(ABC):
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_by_masjid(
            self,
            masjid_id: str,
            *,
            limit: int,
            before_seq: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        pass

    @abstractmethod
    def get_by_id(self, broadcast_id: str) -> Optional[Dict[str, Any]]:
        pass
