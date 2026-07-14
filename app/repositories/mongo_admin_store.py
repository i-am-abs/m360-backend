from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.interfaces.admin_repository import AdminRepository
from app.utils.phone import canonicalize_india_phone, phone_lookup_variants


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
        self._col.create_index([("masjid_place_id", ASCENDING)], sparse=True)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _canonical_phone(phone: str) -> str:
        try:
            return canonicalize_india_phone(phone)
        except ValueError:
            return (phone or "").strip()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now_iso()
        phone = self._canonical_phone(data["phone"])
        payload = {
            "admin_id": str(uuid4()),
            "user_id": data.get("user_id"),
            "name": data["name"],
            "phone": phone,
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
            raise ValueError("This phone number is already an admin") from exc
        return self._public(payload)

    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one({"admin_id": admin_id})
        return self._public(doc) if doc else None

    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        docs = self.list_by_phone(phone)
        return docs[0] if docs else None

    def list_by_phone(
            self,
            phone: str,
            *,
            status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        variants = phone_lookup_variants(phone)
        if not variants:
            return []
        query: Dict[str, Any] = {"phone": {"$in": variants}}
        if status:
            query["status"] = status
        docs = self._col.find(query).sort("created_at", -1)
        return [self._public(doc) for doc in docs]

    def list_approved_for_place(self, place_id: str) -> List[Dict[str, Any]]:
        docs = self._col.find({
            "masjid_place_id": place_id,
            "status": "approved",
        }).sort("created_at", -1)
        return [self._public(doc) for doc in docs]

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
        fields: Dict[str, Any] = {"status": status}
        if updated_by:
            fields["updated_by"] = updated_by
        return self.update_fields(admin_id, fields)

    def update_fields(
            self,
            admin_id: str,
            fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        payload = {**fields, "updated_at": self._now_iso()}
        if "phone" in payload and payload["phone"]:
            payload["phone"] = self._canonical_phone(str(payload["phone"]))
        doc = self._col.find_one_and_update(
            {"admin_id": admin_id},
            {"$set": payload},
            return_document=True,  # type: ignore[call-arg]
        )
        return self._public(doc) if doc else None

    def link_user(self, admin_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return self.update_fields(admin_id, {"user_id": user_id})

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

    def list_by_phone(
            self,
            phone: str,
            *,
            status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return []

    def list_approved_for_place(self, place_id: str) -> List[Dict[str, Any]]:
        return []

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

    def update_fields(
            self,
            admin_id: str,
            fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return None

    def link_user(self, admin_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return None

    def list_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        return []
