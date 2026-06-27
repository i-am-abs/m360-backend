from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VerificationRepository(ABC):
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_status(
            self,
            request_id: str,
            status: str,
            *,
            updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        pass
