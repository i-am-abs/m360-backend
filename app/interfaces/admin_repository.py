from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AdminRepository(ABC):
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new admin registration."""

    @abstractmethod
    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        """Fetch admin by id."""

    @abstractmethod
    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Fetch admin by phone."""

    @abstractmethod
    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List admins, optionally filtered by status."""

    @abstractmethod
    def update_status(
        self,
        admin_id: str,
        status: str,
        *,
        updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update registration status and return updated document."""

    def link_user(self, admin_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Associate an approved admin with a user account."""

    @abstractmethod
    def list_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Return masjid admin assignments for a user."""
