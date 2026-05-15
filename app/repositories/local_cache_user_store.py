from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.interfaces.user_repository import UserRepository


class LocalCacheUserStore(UserRepository):
    def __init__(self) -> None:
        self._lock = RLock()
        self._data: Dict[str, Any] = {
            "users_by_phone": {},
            "favorites_by_user_id": {},
            "sessions": {},
        }

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        with self._lock:
            user = self._data["users_by_phone"].get(phone_number)
            if user is None:
                user = {
                    "user_id": str(uuid4()),
                    "phone_number": phone_number,
                    "created_at": self._now_iso(),
                }
                self._data["users_by_phone"][phone_number] = user
            return user

    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        with self._lock:
            token = str(uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            self._data["sessions"][token] = {
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
            }
            return {"access_token": token, "expires_in": ttl_seconds}

    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._data["sessions"].get(access_token)
            if not session:
                return None
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.now(timezone.utc) >= expires_at:
                del self._data["sessions"][access_token]
                return None
            user_id = session["user_id"]
            for user in self._data["users_by_phone"].values():
                if user.get("user_id") == user_id:
                    return user
            return None

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
