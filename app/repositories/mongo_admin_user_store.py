from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.interfaces.admin_user_repository import AdminUserRepository


class MongoAdminUserStore(AdminUserRepository):
    def __init__(self, collection: Any) -> None:
        self._collection = collection

    def create_admin(self, email: str, password_hash: str, name: str, role: str) -> Dict[str, Any]:
        doc = {
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "name": name,
            "role": role,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login_at": None,
        }
        result = self._collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return doc

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self._collection.find_one({"email": email.lower().strip()})

    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        return self._collection.find_one({"_id": admin_id})

    def list_admins(self) -> List[Dict[str, Any]]:
        return list(self._collection.find({}))

    def update_last_login(self, admin_id: str) -> None:
        self._collection.update_one(
            {"_id": admin_id},
            {"$set": {"last_login_at": datetime.now(timezone.utc).isoformat()}},
        )
