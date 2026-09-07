from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from app.interfaces.admin_user_repository import AdminUserRepository


class InMemoryAdminUserStore(AdminUserRepository):
    def __init__(self) -> None:
        self._admins: Dict[str, Dict[str, Any]] = {}
        self._by_email: Dict[str, str] = {}

    def create_admin(self, email: str, password_hash: str, name: str, role: str) -> Dict[str, Any]:
        admin_id = str(uuid4())
        doc = {
            "_id": admin_id,
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "name": name,
            "role": role,
            "is_active": True,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_login_at": None,
        }
        self._admins[admin_id] = doc
        self._by_email[email.lower().strip()] = admin_id
        return doc

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        admin_id = self._by_email.get(email.lower().strip())
        if not admin_id:
            return None
        return self._admins.get(admin_id)

    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        return self._admins.get(admin_id)

    def list_admins(self) -> List[Dict[str, Any]]:
        return list(self._admins.values())

    def update_last_login(self, admin_id: str) -> None:
        if admin_id in self._admins:
            self._admins[admin_id]["last_login_at"] = "2026-07-01T00:00:00+00:00"


class InMemorySessionsCollection:
    def __init__(self) -> None:
        self._sessions: List[Dict[str, Any]] = []

    def insert_one(self, doc: Dict[str, Any]) -> Any:
        self._sessions.append(doc)
        return None

    def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for s in self._sessions:
            if all(s.get(k) == v for k, v in filter.items()):
                return s
        return None

    def delete_one(self, filter: Dict[str, Any]) -> Any:
        self._sessions[:] = [s for s in self._sessions if not all(s.get(k) == v for k, v in filter.items())]
        return None


@pytest.fixture
def admin_store() -> InMemoryAdminUserStore:
    return InMemoryAdminUserStore()


@pytest.fixture
def sessions() -> InMemorySessionsCollection:
    return InMemorySessionsCollection()
