from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.verification_repository import VerificationRepository


class MongoVerificationStore(VerificationRepository):
    """Collection: ``verification_requests``"""

    _COLLECTION = "verification_requests"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index([("request_id", ASCENDING)], unique=True)
        self._col.create_index([("user_id", ASCENDING)])
        self._col.create_index([("status", ASCENDING)])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now_iso()
        payload = {
            "request_id": str(uuid4()),
            "user_id": data["user_id"],
            "name": data["name"],
            "profile_image": data.get("profile_image"),
            "phone": data["phone"],
            "role": data["role"],
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        self._col.insert_one(payload)
        return self._public(payload)

    def get_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one({"request_id": request_id})
        return self._public(doc) if doc else None

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        docs = self._col.find({"user_id": user_id}).sort("created_at", -1)
        return [self._public(doc) for doc in docs]

    def update_status(
        self,
        request_id: str,
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
            {"request_id": request_id},
            update,
            return_document=True,  # type: ignore[call-arg]
        )
        return self._public(doc) if doc else None

    @staticmethod
    def _public(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not doc:
            return {}
        result = dict(doc)
        result.pop("_id", None)
        return result


class NoOpVerificationStore(VerificationRepository):
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("Verification store unavailable — enable MongoDB")

    def get_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        return None

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        return []

    def update_status(
        self,
        request_id: str,
        status: str,
        *,
        updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return None
