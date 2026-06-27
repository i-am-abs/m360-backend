from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AdminRepository(ABC):
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_status(
            self,
            admin_id: str,
            status: str,
            *,
            updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        pass

    def link_user(self, admin_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        pass
