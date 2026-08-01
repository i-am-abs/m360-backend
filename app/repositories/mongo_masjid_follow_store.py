from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.masjid_follow_repository import MasjidFollowRepository


class MongoMasjidFollowStore(MasjidFollowRepository):
    _COLLECTION = "masjid_follows"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index(
            [("user_id", ASCENDING), ("masjid_id", ASCENDING)],
            unique=True,
            name="user_masjid_unique",
        )
        self._col.create_index([("masjid_id", ASCENDING)])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def follow(self, user_id: str, masjid_id: str) -> None:
        self._col.update_one(
            {"user_id": user_id, "masjid_id": masjid_id},
            {"$setOnInsert": {"created_at": self._now_iso()}},
            upsert=True,
        )

    def unfollow(self, user_id: str, masjid_id: str) -> None:
        self._col.delete_one({"user_id": user_id, "masjid_id": masjid_id})

    def is_following(self, user_id: str, masjid_id: str) -> bool:
        return self._col.find_one(
            {"user_id": user_id, "masjid_id": masjid_id},
            {"_id": 1},
        ) is not None

    def list_follower_user_ids(self, masjid_id: str) -> List[str]:
        cursor = self._col.find({"masjid_id": masjid_id}, {"user_id": 1, "_id": 0})
        return [doc["user_id"] for doc in cursor if doc.get("user_id")]


class NoOpMasjidFollowStore(MasjidFollowRepository):
    def follow(self, user_id: str, masjid_id: str) -> None:
        pass

    def unfollow(self, user_id: str, masjid_id: str) -> None:
        pass

    def is_following(self, user_id: str, masjid_id: str) -> bool:
        return False

    def list_follower_user_ids(self, masjid_id: str) -> List[str]:
        return []
