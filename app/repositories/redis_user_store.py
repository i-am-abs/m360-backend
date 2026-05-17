from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import Settings
from app.interfaces.user_repository import UserRepository


class RedisUserStore(UserRepository):
    def __init__(self, client: Any, settings: Settings) -> None:
        self.redis_client = client
        self.key_prefix = (settings.redis_key_prefix or "m360").strip() or "m360"

    def key_for_phone(self, phone: str) -> str:
        return f"{self.key_prefix}:user:phone:{phone}"

    def key_for_user_id(self, user_id: str) -> str:
        return f"{self.key_prefix}:user:id:{user_id}"

    def key_for_session(self, token: str) -> str:
        return f"{self.key_prefix}:session:{token}"

    def key_for_favorites(self, user_id: str) -> str:
        return f"{self.key_prefix}:favorites:{user_id}"

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        raw = self.redis_client.get(self.key_for_phone(phone_number))
        if raw:
            return json.loads(raw)
        user = {
            "user_id": str(uuid4()),
            "phone_number": phone_number,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        blob = json.dumps(user)
        self.redis_client.set(self.key_for_phone(phone_number), blob)
        self.redis_client.set(self.key_for_user_id(user["user_id"]), blob)
        return user

    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        token = str(uuid4())
        self.redis_client.setex(self.key_for_session(token), ttl_seconds, user_id)
        return {"access_token": token, "expires_in": ttl_seconds}

    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        user_id = self.redis_client.get(self.key_for_session(access_token))
        if not user_id:
            return None
        raw = self.redis_client.get(self.key_for_user_id(user_id))
        if not raw:
            return None
        return json.loads(raw)

    def list_favorites(self, user_id: str) -> List[str]:
        raw = self.redis_client.get(self.key_for_favorites(user_id))
        if not raw:
            return []
        data = json.loads(raw)
        return list(data) if isinstance(data, list) else []

    def add_favorite(self, user_id: str, place_id: str) -> List[str]:
        favs = self.list_favorites(user_id)
        if place_id not in favs:
            favs.append(place_id)
        self.redis_client.set(self.key_for_favorites(user_id), json.dumps(favs))
        return list(favs)

    def remove_favorite(self, user_id: str, place_id: str) -> List[str]:
        favs = [p for p in self.list_favorites(user_id) if p != place_id]
        self.redis_client.set(self.key_for_favorites(user_id), json.dumps(favs))
        return favs
