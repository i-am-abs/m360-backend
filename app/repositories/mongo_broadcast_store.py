from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database

from app.interfaces.broadcast_repository import BroadcastRepository


class MongoBroadcastStore(BroadcastRepository):
    _COLLECTION = "broadcasts"
    _COUNTERS = "counters"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._counters = db[self._COUNTERS]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index([("broadcast_id", ASCENDING)], unique=True)
        self._col.create_index(
            [("masjid_id", ASCENDING), ("seq", DESCENDING)],
            name="masjid_feed",
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _next_seq(self, masjid_id: str) -> int:
        doc = self._counters.find_one_and_update(
            {"_id": f"broadcast:{masjid_id}"},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(doc["value"])

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        masjid_id = data["masjid_id"]
        payload = {
            "broadcast_id": str(uuid4()),
            "masjid_id": masjid_id,
            "caption": data["caption"],
            "video_uri": data.get("video_uri"),
            "thumbnail_uri": data.get("thumbnail_uri"),
            "message_type": data.get("message_type", "text"),
            "created_by": data.get("created_by"),
            "seq": self._next_seq(masjid_id),
            "created_at": self._now_iso(),
        }
        self._col.insert_one(payload)
        return self._public(payload)

    def list_by_masjid(
            self,
            masjid_id: str,
            *,
            limit: int,
            before_seq: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        query: Dict[str, Any] = {"masjid_id": masjid_id}
        if before_seq is not None:
            query["seq"] = {"$lt": before_seq}

        # Fetch one extra to determine has_more without a second query.
        docs = list(
            self._col.find(query)
            .sort("seq", DESCENDING)
            .limit(limit + 1)
        )
        has_more = len(docs) > limit
        items = [self._public(doc) for doc in docs[:limit]]
        return items, has_more

    def get_by_id(self, broadcast_id: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one({"broadcast_id": broadcast_id})
        return self._public(doc) if doc else None

    @staticmethod
    def _public(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not doc:
            return {}
        result = dict(doc)
        result.pop("_id", None)
        return result


class NoOpBroadcastStore(BroadcastRepository):
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("Broadcast store unavailable — enable MongoDB")

    def list_by_masjid(
            self,
            masjid_id: str,
            *,
            limit: int,
            before_seq: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        return [], False

    def get_by_id(self, broadcast_id: str) -> Optional[Dict[str, Any]]:
        return None
