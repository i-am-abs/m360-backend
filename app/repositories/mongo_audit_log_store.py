from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.interfaces.audit_log_repository import AuditLogRepository


class MongoAuditLogStore(AuditLogRepository):
    """Collection: ``audit_logs``"""

    _COLLECTION = "audit_logs"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index(
            [("resource_type", ASCENDING), ("resource_id", ASCENDING)],
            name="resource_lookup",
        )
        self._col.create_index([("created_at", DESCENDING)])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def write(self, entry: Dict[str, Any]) -> None:
        payload = {
            "audit_id": str(uuid4()),
            "action": entry["action"],
            "resource_type": entry["resource_type"],
            "resource_id": entry["resource_id"],
            "user_id": entry.get("user_id"),
            "details": entry.get("details", {}),
            "created_at": self._now_iso(),
        }
        self._col.insert_one(payload)

    def list_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        docs = (
            self._col.find({
                "resource_type": resource_type,
                "resource_id": resource_id,
            })
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return [{k: v for k, v in doc.items() if k != "_id"} for doc in docs]


class NoOpAuditLogStore(AuditLogRepository):
    def write(self, entry: Dict[str, Any]) -> None:
        pass

    def list_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        return []
