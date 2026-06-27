from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.fcm_token_repository import FcmTokenRepository


class MongoFcmTokenStore(FcmTokenRepository):
    """Collection: ``fcm_tokens`` — maps device tokens to users.

    Document shape::

        { "token": str, "user_id": str, "platform": str | None, "updated_at": str }
    """

    _COLLECTION = "fcm_tokens"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index([("token", ASCENDING)], unique=True)
        self._col.create_index([("user_id", ASCENDING)])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def register(self, user_id: str, token: str, platform: str | None = None) -> None:
        self._col.update_one(
            {"token": token},
            {
                "$set": {
                    "user_id": user_id,
                    "platform": platform,
                    "updated_at": self._now_iso(),
                }
            },
            upsert=True,
        )

    def list_tokens_for_users(self, user_ids: List[str]) -> List[str]:
        if not user_ids:
            return []
        cursor = self._col.find(
            {"user_id": {"$in": user_ids}},
            {"token": 1, "_id": 0},
        )
        return [doc["token"] for doc in cursor if doc.get("token")]

    def remove(self, token: str) -> None:
        self._col.delete_one({"token": token})


class NoOpFcmTokenStore(FcmTokenRepository):
    def register(self, user_id: str, token: str, platform: str | None = None) -> None:
        pass

    def list_tokens_for_users(self, user_ids: List[str]) -> List[str]:
        return []

    def remove(self, token: str) -> None:
        pass
