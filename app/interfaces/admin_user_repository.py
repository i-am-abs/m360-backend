from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AdminUserRepository(ABC):
    @abstractmethod
    def create_admin(self, email: str, password_hash: str, name: str, role: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_admins(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_last_login(self, admin_id: str) -> None:
        pass
