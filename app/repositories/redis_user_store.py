from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from redis import Redis

from app.core.config import Settings
from app.interfaces.user_repository import UserRepository
from app.utils.session_ttl import session_expires_in, session_never_expires


class RedisUserStore(UserRepository):
    def __init__(self, client: Redis, settings: Settings) -> None:
        self._r = client
        self._pfx = (settings.redis_key_prefix or "m360").strip() or "m360"

    def _key_phone(self, phone: str) -> str:
        return f"{self._pfx}:user:phone:{phone}"

    def _key_user_id(self, user_id: str) -> str:
        return f"{self._pfx}:user:id:{user_id}"

    def _key_session(self, token: str) -> str:
        return f"{self._pfx}:session:{token}"

    def _key_favorites(self, user_id: str) -> str:
        return f"{self._pfx}:favorites:{user_id}"

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        raw = self._r.get(self._key_phone(phone_number))
        if raw:
            return json.loads(raw)
        user = {
            "user_id": str(uuid4()),
            "phone_number": phone_number,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        blob = json.dumps(user)
        self._r.set(self._key_phone(phone_number), blob)
        self._r.set(self._key_user_id(user["user_id"]), blob)
        return user

    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        token = str(uuid4())
        key = self._key_session(token)
        if session_never_expires(ttl_seconds):
            self._r.set(key, user_id)
        else:
            self._r.setex(key, ttl_seconds, user_id)
        return {"access_token": token, "expires_in": session_expires_in(ttl_seconds)}

    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        user_id = self._r.get(self._key_session(access_token))
        if not user_id:
            return None
        raw = self._r.get(self._key_user_id(user_id))
        if not raw:
            return None
        return json.loads(raw)

    def resolve_session_user_id(self, access_token: str) -> Optional[str]:
        user_id = self._r.get(self._key_session(access_token))
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
        self._r.delete(self._key_session(access_token))
        return self.create_session(user_id, ttl_seconds)

    def list_favorites(self, user_id: str) -> List[str]:
        raw = self._r.get(self._key_favorites(user_id))
        if not raw:
            return []
        data = json.loads(raw)
        return list(data) if isinstance(data, list) else []

    def add_favorite(self, user_id: str, place_id: str) -> List[str]:
        favs = self.list_favorites(user_id)
        if place_id not in favs:
            favs.append(place_id)
        self._r.set(self._key_favorites(user_id), json.dumps(favs))
        return list(favs)

    def remove_favorite(self, user_id: str, place_id: str) -> List[str]:
        favs = [p for p in self.list_favorites(user_id) if p != place_id]
        self._r.set(self._key_favorites(user_id), json.dumps(favs))
        return favs
