from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.interfaces.admin_repository import AdminRepository


class MongoAdminStore(AdminRepository):
    _COLLECTION = "admins"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index([("admin_id", ASCENDING)], unique=True)
        self._col.create_index([("phone", ASCENDING)], unique=True)
        self._col.create_index([("user_id", ASCENDING)], sparse=True)
        self._col.create_index([("status", ASCENDING)])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now_iso()
        payload = {
            "admin_id": str(uuid4()),
            "user_id": data.get("user_id"),
            "name": data["name"],
            "phone": data["phone"],
            "profile_image": data.get("profile_image"),
            "role": data["role"],
            "committee_id": data.get("committee_id"),
            "masjid_place_id": data.get("masjid_place_id"),
            "status": data.get("status", "pending"),
            "created_at": now,
            "updated_at": now,
        }
        try:
            self._col.insert_one(payload)
        except DuplicateKeyError as exc:
            raise ValueError("Admin with this phone already exists") from exc
        return self._public(payload)

    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one({"admin_id": admin_id})
        return self._public(doc) if doc else None

    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one({"phone": phone})
        return self._public(doc) if doc else None

    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status
        docs = self._col.find(query).sort("created_at", -1)
        return [self._public(doc) for doc in docs]

    def update_status(
            self,
            admin_id: str,
            status: str,
            *,
            updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        update: Dict[str, Any] = {
            "$set": {
                "status": status,
                "updated_at": self._now_iso(),
            },
        }
        if updated_by:
            update["$set"]["updated_by"] = updated_by
        doc = self._col.find_one_and_update(
            {"admin_id": admin_id},
            update,
            return_document=True,  # type: ignore[call-arg]
        )
        return self._public(doc) if doc else None

    def link_user(self, admin_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one_and_update(
            {"admin_id": admin_id},
            {"$set": {"user_id": user_id, "updated_at": self._now_iso()}},
            return_document=True,  # type: ignore[call-arg]
        )
        return self._public(doc) if doc else None

    def list_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        docs = self._col.find({
            "user_id": user_id,
            "status": "approved",
        })
        return [self._public(doc) for doc in docs]

    @staticmethod
    def _public(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not doc:
            return {}
        result = dict(doc)
        result.pop("_id", None)
        return result


class NoOpAdminStore(AdminRepository):
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("Admin store unavailable — enable MongoDB")

    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        return None

    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def update_status(
            self,
            admin_id: str,
            status: str,
            *,
            updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return None

    def link_user(self, admin_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return None

    def list_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        return []
