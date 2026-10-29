from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ShareRepository(ABC):
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_by_share_id(self, share_id: str) -> Optional[Dict[str, Any]]:
        pass
