from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.interfaces.user_repository import UserRepository
from app.repositories.user_store_helpers import (
    merge_favorite_place_ids,
    pick_primary_user,
    resolve_canonical_phone,
)
from app.utils.phone import phone_lookup_variants
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
        self._favorites.create_index([("phone_number", ASCENDING)], unique=True, sparse=True)
        self._favorites.create_index([("user_id", ASCENDING)], unique=True, sparse=True)

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        canonical_phone = resolve_canonical_phone(phone_number)
        variants = phone_lookup_variants(canonical_phone)
        docs = list(self._users.find({"phone_number": {"$in": variants}}))
        if not docs:
            user_id = str(uuid4())
            payload = {
                "user_id": user_id,
                "phone_number": canonical_phone,
                "created_at": self._now_iso(),
            }
            try:
                self._users.insert_one(payload)
            except DuplicateKeyError:
                doc = self._users.find_one({"phone_number": canonical_phone})
                if doc:
                    return self._as_user_dict(doc)
                raise
            return payload

        matches = [(str(doc["phone_number"]), self._as_user_dict(doc)) for doc in docs]
        primary_key, primary_user, duplicates = pick_primary_user(matches)
        primary_user_id = str(primary_user["user_id"])
        favorite_lists = [self.list_favorites(canonical_phone)]
        duplicate_user_ids: list[str] = []
        for _dup_key, dup_user in duplicates:
            dup_user_id = str(dup_user.get("user_id") or "")
            if not dup_user_id:
                continue
            duplicate_user_ids.append(dup_user_id)
            favorite_lists.append(self._list_legacy_favorites(dup_user_id))

        merged_favorites = merge_favorite_place_ids(*favorite_lists)
        if merged_favorites:
            self._favorites.update_one(
                {"phone_number": canonical_phone},
                {
                    "$set": {"place_ids": merged_favorites, "phone_number": canonical_phone},
                    "$unset": {"user_id": ""},
                },
                upsert=True,
            )
        for dup_user_id in duplicate_user_ids:
            self._favorites.delete_one({"user_id": dup_user_id})
            self._users.delete_one({"user_id": dup_user_id})
        self._favorites.delete_one({"user_id": primary_user_id})

        if primary_user.get("phone_number") != canonical_phone:
            self._users.update_one(
                {"user_id": primary_user_id},
                {"$set": {"phone_number": canonical_phone}},
            )
            primary_user["phone_number"] = canonical_phone
        return primary_user

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

    def _list_legacy_favorites(self, user_id: str) -> List[str]:
        doc = self._favorites.find_one({"user_id": user_id})
        if not doc:
            return []
        return list(doc.get("place_ids") or [])

    def _migrate_favorites_for_phone(self, phone_number: str) -> List[str]:
        phone = resolve_canonical_phone(phone_number)
        doc = self._favorites.find_one({"phone_number": phone})
        if doc:
            return list(doc.get("place_ids") or [])

        variants = phone_lookup_variants(phone)
        user_docs = list(self._users.find({"phone_number": {"$in": variants}}))
        favorite_lists: List[List[str]] = []
        legacy_user_ids: list[str] = []
        for user_doc in user_docs:
            user_id = str(user_doc.get("user_id") or "")
            if not user_id:
                continue
            legacy = self._list_legacy_favorites(user_id)
            if legacy:
                favorite_lists.append(legacy)
                legacy_user_ids.append(user_id)

        if not favorite_lists:
            return []

        merged = merge_favorite_place_ids(*favorite_lists)
        self._favorites.update_one(
            {"phone_number": phone},
            {"$set": {"place_ids": merged, "phone_number": phone}, "$unset": {"user_id": ""}},
            upsert=True,
        )
        for user_id in legacy_user_ids:
            self._favorites.delete_one({"user_id": user_id})
        return merged

    def list_favorites(self, phone_number: str) -> List[str]:
        from app.core.enums.masjid import MasjidSaveLimit

        favorites = self._migrate_favorites_for_phone(phone_number)
        max_favorites = MasjidSaveLimit.MAX_FAVORITES.value
        if len(favorites) <= max_favorites:
            return favorites
        favorites = favorites[:max_favorites]
        phone = resolve_canonical_phone(phone_number)
        self._favorites.update_one(
            {"phone_number": phone},
            {"$set": {"place_ids": favorites}},
        )
        return favorites

    def add_favorite(self, phone_number: str, place_id: str) -> List[str]:
        phone = resolve_canonical_phone(phone_number)
        self._favorites.update_one(
            {"phone_number": phone},
            {
                "$addToSet": {"place_ids": place_id},
                "$set": {"phone_number": phone},
                "$unset": {"user_id": ""},
            },
            upsert=True,
        )
        return self.list_favorites(phone)

    def remove_favorite(self, phone_number: str, place_id: str) -> List[str]:
        phone = resolve_canonical_phone(phone_number)
        self._favorites.update_one(
            {"phone_number": phone},
            {"$pull": {"place_ids": place_id}},
        )
        return self.list_favorites(phone)

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
