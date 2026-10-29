from __future__ import annotations

from typing import Any, Dict, Optional

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.share_repository import ShareRepository


class MongoShareRepository(ShareRepository):
    def __init__(self, db: Database) -> None:
        self._col = db["shares"]
        self._col.create_index([("share_id", ASCENDING)], unique=True)
        self._col.create_index([("message_id", ASCENDING), ("created_at", ASCENDING)])
        self._col.create_index([("root_share_id", ASCENDING)])

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(data)
        self._col.insert_one(payload)
        payload.pop("_id", None)
        return payload

    def get_by_share_id(self, share_id: str) -> Optional[Dict[str, Any]]:
        if not share_id:
            return None
        doc = self._col.find_one({"share_id": share_id}, {"_id": 0})
        return dict(doc) if doc else None
