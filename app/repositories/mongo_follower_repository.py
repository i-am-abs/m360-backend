from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.follower_repository import FollowerRepository


class MongoFollowerRepository(FollowerRepository):
    def __init__(self, db: Database) -> None:
        self._followers = db["masjid_followers"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._followers.create_index([("user_id", ASCENDING), ("masjid_id", ASCENDING)], unique=True)
        self._followers.create_index([("masjid_id", ASCENDING)])

    def follow(self, user_id: str, masjid_id: str, notifications_enabled: bool) -> dict:
        doc = {
            "user_id": user_id,
            "masjid_id": masjid_id,
            "notifications_enabled": notifications_enabled,
            "followed_at": self._now_iso(),
        }
        self._followers.update_one(
            {"user_id": user_id, "masjid_id": masjid_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return doc

    def unfollow(self, user_id: str, masjid_id: str) -> bool:
        result = self._followers.delete_one({"user_id": user_id, "masjid_id": masjid_id})
        return result.deleted_count > 0

    def is_following(self, user_id: str, masjid_id: str) -> bool:
        doc = self._followers.find_one({"user_id": user_id, "masjid_id": masjid_id})
        return doc is not None

    def get_followers_count(self, masjid_id: str) -> int:
        return self._followers.count_documents({"masjid_id": masjid_id})

    def get_follower_ids(self, masjid_id: str) -> List[str]:
        docs = self._followers.find({"masjid_id": masjid_id}, {"user_id": 1, "_id": 0})
        return [doc["user_id"] for doc in docs]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()