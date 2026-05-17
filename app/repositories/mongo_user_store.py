from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.interfaces.user_repository import UserRepository
from app.utils.session_ttl import session_expires_in, session_never_expires


class MongoUserStore(UserRepository):
    def __init__(self, db: Database) -> None:
        self._users = db["users"]
        self._sessions = db["sessions"]
        self._favorites = db["favorites"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._users.create_index([("phone_number", ASCENDING)], unique=True)
        self._users.create_index([("user_id", ASCENDING)], unique=True)
        self._sessions.create_index([("access_token", ASCENDING)], unique=True)
        self._sessions.create_index("expires_at", expireAfterSeconds=0)
        self._favorites.create_index([("user_id", ASCENDING)], unique=True)

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        doc = self._users.find_one({"phone_number": phone_number})
        if doc:
            return self._as_user_dict(doc)
        user_id = str(uuid4())
        payload = {
            "user_id": user_id,
            "phone_number": phone_number,
            "created_at": self._now_iso(),
        }
        try:
            self._users.insert_one(payload)
        except DuplicateKeyError:
            doc = self._users.find_one({"phone_number": phone_number})
            if doc:
                return self._as_user_dict(doc)
            raise
        return payload

    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        token = str(uuid4())
        payload: Dict[str, Any] = {
            "access_token": token,
            "user_id": user_id,
        }
        if not session_never_expires(ttl_seconds):
            payload["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._sessions.insert_one(payload)
        return {"access_token": token, "expires_in": session_expires_in(ttl_seconds)}

    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        sess = self._sessions.find_one({"access_token": access_token})
        if not sess:
            return None
        if not self._session_is_active(sess):
            self._sessions.delete_one({"access_token": access_token})
            return None
        user_id = sess.get("user_id")
        if not user_id:
            return None
        doc = self._users.find_one({"user_id": user_id})
        return self._as_user_dict(doc) if doc else None

    def resolve_session_user_id(self, access_token: str) -> Optional[str]:
        sess = self._sessions.find_one({"access_token": access_token})
        if not sess:
            return None
        user_id = sess.get("user_id")
        return str(user_id) if user_id else None

    def refresh_session(self, access_token: str, ttl_seconds: int) -> Optional[Dict[str, Any]]:
        user_id = self.resolve_session_user_id(access_token)
        if not user_id:
            return None
        if session_never_expires(ttl_seconds):
            return {
                "access_token": access_token,
                "expires_in": session_expires_in(ttl_seconds),
            }
        self._sessions.delete_one({"access_token": access_token})
        return self.create_session(user_id, ttl_seconds)

    def _session_is_active(self, sess: Dict[str, Any]) -> bool:
        exp = sess.get("expires_at")
        if exp is None:
            return True
        if not isinstance(exp, datetime):
            return True
        return exp > datetime.now(timezone.utc)

    def list_favorites(self, user_id: str) -> List[str]:
        doc = self._favorites.find_one({"user_id": user_id})
        if not doc:
            return []
        return list(doc.get("place_ids") or [])

    def add_favorite(self, user_id: str, place_id: str) -> List[str]:
        self._favorites.update_one(
            {"user_id": user_id},
            {"$addToSet": {"place_ids": place_id}, "$setOnInsert": {"user_id": user_id}},
            upsert=True,
        )
        return self.list_favorites(user_id)

    def remove_favorite(self, user_id: str, place_id: str) -> List[str]:
        self._favorites.update_one(
            {"user_id": user_id},
            {"$pull": {"place_ids": place_id}},
        )
        return self.list_favorites(user_id)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _as_user_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_id": doc["user_id"],
            "phone_number": doc["phone_number"],
            "created_at": doc["created_at"],
        }
