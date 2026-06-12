from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from redis import Redis

from app.core.config import Settings
from app.interfaces.user_repository import UserRepository
from app.repositories.user_store_helpers import (
    merge_favorite_place_ids,
    pick_primary_user,
    resolve_canonical_phone,
)
from app.utils.phone import phone_lookup_variants
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

    def _key_favorites(self, phone: str) -> str:
        canonical = resolve_canonical_phone(phone)
        return f"{self._pfx}:favorites:phone:{canonical}"

    def _key_legacy_favorites(self, user_id: str) -> str:
        return f"{self._pfx}:favorites:{user_id}"

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        canonical_phone = resolve_canonical_phone(phone_number)
        matches: list[tuple[str, Dict[str, Any]]] = []
        for variant in phone_lookup_variants(canonical_phone):
            raw = self._r.get(self._key_phone(variant))
            if not raw:
                continue
            user = json.loads(raw)
            user_id = str(user.get("user_id") or "")
            if any(existing[1].get("user_id") == user_id for existing in matches):
                continue
            matches.append((variant, user))

        if not matches:
            user = {
                "user_id": str(uuid4()),
                "phone_number": canonical_phone,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            blob = json.dumps(user)
            self._r.set(self._key_phone(canonical_phone), blob)
            self._r.set(self._key_user_id(user["user_id"]), blob)
            return user

        primary_key, primary_user, duplicates = pick_primary_user(matches)
        primary_user_id = str(primary_user["user_id"])
        favorite_lists = [self.list_favorites(canonical_phone)]
        for dup_key, dup_user in duplicates:
            dup_user_id = str(dup_user.get("user_id") or "")
            if dup_user_id:
                favorite_lists.append(self._list_legacy_favorites(dup_user_id))
                self._r.delete(self._key_legacy_favorites(dup_user_id))
                self._r.delete(self._key_user_id(dup_user_id))
            if dup_key != canonical_phone:
                self._r.delete(self._key_phone(dup_key))

        merged_favorites = merge_favorite_place_ids(*favorite_lists)
        if merged_favorites:
            self._r.set(self._key_favorites(canonical_phone), json.dumps(merged_favorites))
        self._r.delete(self._key_legacy_favorites(primary_user_id))

        if primary_key != canonical_phone:
            self._r.delete(self._key_phone(primary_key))
        primary_user["phone_number"] = canonical_phone
        blob = json.dumps(primary_user)
        self._r.set(self._key_phone(canonical_phone), blob)
        self._r.set(self._key_user_id(primary_user_id), blob)
        return primary_user

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

    def _list_legacy_favorites(self, user_id: str) -> List[str]:
        raw = self._r.get(self._key_legacy_favorites(user_id))
        if not raw:
            return []
        data = json.loads(raw)
        return list(data) if isinstance(data, list) else []

    def _migrate_favorites_for_phone(self, phone_number: str) -> List[str]:
        phone = resolve_canonical_phone(phone_number)
        raw = self._r.get(self._key_favorites(phone))
        if raw:
            data = json.loads(raw)
            return list(data) if isinstance(data, list) else []

        favorite_lists: List[List[str]] = []
        legacy_keys: list[str] = []
        for variant in phone_lookup_variants(phone):
            user_raw = self._r.get(self._key_phone(variant))
            if not user_raw:
                continue
            user = json.loads(user_raw)
            user_id = str(user.get("user_id") or "")
            if not user_id:
                continue
            legacy = self._list_legacy_favorites(user_id)
            if legacy:
                favorite_lists.append(legacy)
                legacy_keys.append(self._key_legacy_favorites(user_id))

        if not favorite_lists:
            return []

        merged = merge_favorite_place_ids(*favorite_lists)
        self._r.set(self._key_favorites(phone), json.dumps(merged))
        for key in legacy_keys:
            self._r.delete(key)
        return merged

    def list_favorites(self, phone_number: str) -> List[str]:
        from app.core.enums.masjid import MasjidSaveLimit

        favorites = self._migrate_favorites_for_phone(phone_number)
        max_favorites = MasjidSaveLimit.MAX_FAVORITES.value
        if len(favorites) <= max_favorites:
            return favorites
        favorites = favorites[:max_favorites]
        self._r.set(self._key_favorites(phone_number), json.dumps(favorites))
        return favorites

    def add_favorite(self, phone_number: str, place_id: str) -> List[str]:
        favs = self.list_favorites(phone_number)
        if place_id not in favs:
            favs.append(place_id)
        self._r.set(self._key_favorites(phone_number), json.dumps(favs))
        return list(favs)

    def remove_favorite(self, phone_number: str, place_id: str) -> List[str]:
        favs = [p for p in self.list_favorites(phone_number) if p != place_id]
        self._r.set(self._key_favorites(phone_number), json.dumps(favs))
        return favs
