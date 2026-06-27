from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.masjid_listing_repository import MasjidListingRepository


class MongoMasjidListingStore(MasjidListingRepository):
    _COLLECTION = "masjid_listings"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index([("place_id", ASCENDING)], unique=True)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_listing(self, place_id: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one({"place_id": place_id})
        return self._public(doc) if doc else None

    def upsert_listing(self, place_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now_iso()
        payload = {
            "admin_status": data.get("admin_status", {
                "label": "unverified",
                "message": "",
            }),
            "tag": data.get("tag"),
            "message": data.get("message"),
            "updated_at": now,
        }
        result = self._col.find_one_and_update(
            {"place_id": place_id},
            {
                "$set": payload,
                "$setOnInsert": {"place_id": place_id, "created_at": now},
            },
            upsert=True,
            return_document=True,  # type: ignore[call-arg]
        )
        return self._public(result)

    def list_by_place_ids(self, place_ids: List[str]) -> List[Dict[str, Any]]:
        if not place_ids:
            return []
        docs = self._col.find({"place_id": {"$in": place_ids}})
        return [self._public(doc) for doc in docs]

    @staticmethod
    def _public(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not doc:
            return {}
        result = dict(doc)
        result.pop("_id", None)
        return result


class NoOpMasjidListingStore(MasjidListingRepository):
    def get_listing(self, place_id: str) -> Optional[Dict[str, Any]]:
        return None

    def upsert_listing(self, place_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return data

    def list_by_place_ids(self, place_ids: List[str]) -> List[Dict[str, Any]]:
        return []
