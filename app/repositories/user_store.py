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
        with self._lock:
            data = self._read()
            user = data["users_by_phone"].get(phone_number)
            if user is None:
                user = {
                    "user_id": str(uuid4()),
                    "phone_number": phone_number,
                    "created_at": self._now_iso(),
                }
                data["users_by_phone"][phone_number] = user
                self._write(data)
            return user

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
