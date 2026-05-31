from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.interfaces.user_repository import UserRepository
from app.repositories.user_store_helpers import (
    find_matching_users,
    merge_favorite_place_ids,
    pick_primary_user,
    resolve_canonical_phone,
)
from app.utils.session_ttl import session_expires_in, session_never_expires


class LocalCacheUserStore(UserRepository):
    def __init__(self) -> None:
        self._lock = RLock()
        self._data: Dict[str, Any] = {
            "users_by_phone": {},
            "favorites_by_user_id": {},
            "sessions": {},
        }

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        canonical_phone = resolve_canonical_phone(phone_number)
        with self._lock:
            matches = find_matching_users(self._data["users_by_phone"], canonical_phone)
            if not matches:
                user = {
                    "user_id": str(uuid4()),
                    "phone_number": canonical_phone,
                    "created_at": self._now_iso(),
                }
                self._data["users_by_phone"][canonical_phone] = user
                return user

            primary_key, primary_user, duplicates = pick_primary_user(matches)
            primary_user_id = str(primary_user["user_id"])
            favorite_lists = [
                self._data["favorites_by_user_id"].get(primary_user_id, []),
            ]
            for dup_key, dup_user in duplicates:
                dup_user_id = str(dup_user.get("user_id") or "")
                if dup_user_id:
                    favorite_lists.append(
                        self._data["favorites_by_user_id"].get(dup_user_id, []),
                    )
                    self._data["favorites_by_user_id"].pop(dup_user_id, None)
                if dup_key != canonical_phone:
                    self._data["users_by_phone"].pop(dup_key, None)

            merged_favorites = merge_favorite_place_ids(*favorite_lists)
            if merged_favorites:
                self._data["favorites_by_user_id"][primary_user_id] = merged_favorites

            if primary_key != canonical_phone:
                self._data["users_by_phone"].pop(primary_key, None)
            primary_user["phone_number"] = canonical_phone
            self._data["users_by_phone"][canonical_phone] = primary_user
            return primary_user

    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        with self._lock:
            token = str(uuid4())
            entry: Dict[str, Any] = {"user_id": user_id}
            if not session_never_expires(ttl_seconds):
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
                entry["expires_at"] = expires_at.isoformat()
            self._data["sessions"][token] = entry
            return {"access_token": token, "expires_in": session_expires_in(ttl_seconds)}

    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._data["sessions"].get(access_token)
            if not session:
                return None
            if not self._session_is_active(session):
                del self._data["sessions"][access_token]
                return None
            user_id = session["user_id"]
            for user in self._data["users_by_phone"].values():
                if user.get("user_id") == user_id:
                    return user
            return None

    def resolve_session_user_id(self, access_token: str) -> Optional[str]:
        with self._lock:
            session = self._data["sessions"].get(access_token)
            if not session:
                return None
            user_id = session.get("user_id")
            return str(user_id) if user_id else None

    def refresh_session(self, access_token: str, ttl_seconds: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            user_id = self.resolve_session_user_id(access_token)
            if not user_id:
                return None
            if session_never_expires(ttl_seconds):
                return {
                    "access_token": access_token,
                    "expires_in": session_expires_in(ttl_seconds),
                }
            del self._data["sessions"][access_token]
        return self.create_session(user_id, ttl_seconds)

    @staticmethod
    def _session_is_active(session: Dict[str, Any]) -> bool:
        raw = session.get("expires_at")
        if not raw:
            return True
        expires_at = datetime.fromisoformat(raw)
        return datetime.now(timezone.utc) < expires_at

    def list_favorites(self, user_id: str) -> List[str]:
        with self._lock:
            return list(self._data["favorites_by_user_id"].get(user_id, []))

    def add_favorite(self, user_id: str, place_id: str) -> List[str]:
        with self._lock:
            favorites = self._data["favorites_by_user_id"].setdefault(user_id, [])
            if place_id not in favorites:
                favorites.append(place_id)
            return list(favorites)

    def remove_favorite(self, user_id: str, place_id: str) -> List[str]:
        with self._lock:
            favorites = self._data["favorites_by_user_id"].setdefault(user_id, [])
            self._data["favorites_by_user_id"][user_id] = [
                pid for pid in favorites if pid != place_id
            ]
            return list(self._data["favorites_by_user_id"][user_id])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
