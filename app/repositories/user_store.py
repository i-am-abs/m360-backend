from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.interfaces.user_repository import UserRepository
from app.repositories.user_store_helpers import find_matching_users, merge_favorite_place_ids, pick_primary_user, resolve_canonical_phone
from app.utils.session_ttl import session_expires_in, session_never_expires


class JsonFileUserStore(UserRepository):
    def __init__(self, file_path: str) -> None:
        if not file_path:
            raise ApiException(
                "USER_STORE_FILE is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
                code=ErrorCode.CONFIG_MISSING,
            )
        self._path = file_path
        self._lock = RLock()
        self._bootstrap()

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        canonical_phone = resolve_canonical_phone(phone_number)
        with self._lock:
            data = self._read()
            matches = find_matching_users(data["users_by_phone"], canonical_phone)
            if not matches:
                user = {
                    "user_id": str(uuid4()),
                    "phone_number": canonical_phone,
                    "created_at": self._now_iso(),
                }
                data["users_by_phone"][canonical_phone] = user
                self._write(data)
                return user

            primary_key, primary_user, duplicates = pick_primary_user(matches)
            primary_user_id = str(primary_user["user_id"])
            favorite_lists = [
                data["favorites_by_user_id"].get(primary_user_id, []),
            ]
            for dup_key, dup_user in duplicates:
                dup_user_id = str(dup_user.get("user_id") or "")
                if dup_user_id:
                    favorite_lists.append(
                        data["favorites_by_user_id"].get(dup_user_id, []),
                    )
                    data["favorites_by_user_id"].pop(dup_user_id, None)
                if dup_key != canonical_phone:
                    data["users_by_phone"].pop(dup_key, None)

            merged_favorites = merge_favorite_place_ids(*favorite_lists)
            if merged_favorites:
                data["favorites_by_user_id"][primary_user_id] = merged_favorites

            if primary_key != canonical_phone:
                data["users_by_phone"].pop(primary_key, None)
            primary_user["phone_number"] = canonical_phone
            data["users_by_phone"][canonical_phone] = primary_user
            self._write(data)
            return primary_user

    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            token = str(uuid4())
            entry: Dict[str, Any] = {"user_id": user_id}
            if not session_never_expires(ttl_seconds):
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
                entry["expires_at"] = expires_at.isoformat()
            data["sessions"][token] = entry
            self._write(data)
            return {"access_token": token, "expires_in": session_expires_in(ttl_seconds)}

    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            session = data["sessions"].get(access_token)
            if not session:
                return None
            if not self._session_is_active(session):
                del data["sessions"][access_token]
                self._write(data)
                return None
            user_id = session["user_id"]
            for user in data["users_by_phone"].values():
                if user.get("user_id") == user_id:
                    return user
            return None

    def resolve_session_user_id(self, access_token: str) -> Optional[str]:
        with self._lock:
            data = self._read()
            session = data["sessions"].get(access_token)
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
            data = self._read()
            data["sessions"].pop(access_token, None)
            self._write(data)
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
            data = self._read()
            return list(data["favorites_by_user_id"].get(user_id, []))

    def add_favorite(self, user_id: str, place_id: str) -> List[str]:
        with self._lock:
            data = self._read()
            favorites = data["favorites_by_user_id"].setdefault(user_id, [])
            if place_id not in favorites:
                favorites.append(place_id)
                self._write(data)
            return list(favorites)

    def remove_favorite(self, user_id: str, place_id: str) -> List[str]:
        with self._lock:
            data = self._read()
            favorites = data["favorites_by_user_id"].setdefault(user_id, [])
            data["favorites_by_user_id"][user_id] = [
                pid for pid in favorites if pid != place_id
            ]
            self._write(data)
            return list(data["favorites_by_user_id"][user_id])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _bootstrap(self) -> None:
        with self._lock:
            parent = os.path.dirname(self._path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if not os.path.exists(self._path):
                self._write({
                    "users_by_phone": {},
                    "favorites_by_user_id": {},
                    "sessions": {},
                })

    def _read(self) -> Dict[str, Any]:
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, payload: Dict[str, Any]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)
