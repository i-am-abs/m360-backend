from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import bcrypt

from app.interfaces.admin_user_repository import AdminUserRepository


class AdminAuthService:
    def __init__(self, token_ttl_seconds: int, collection: Any, admin_store: AdminUserRepository) -> None:
        self._token_ttl = token_ttl_seconds
        self._collection = collection
        self._admin_store = admin_store

    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        admin = self._admin_store.get_by_email(email)
        if not admin:
            return None
        if not admin.get("is_active", True):
            return None
        if not bcrypt.checkpw(password.encode(), admin["password_hash"].encode()):
            return None
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now.timestamp() + self._token_ttl
        self._collection.insert_one({
            "admin_id": admin["_id"],
            "token": token,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "is_admin_session": True,
        })
        return {"admin": admin, "token": token}

    def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        session = self._collection.find_one({"token": token, "is_admin_session": True})
        if not session:
            return None
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts > session["expires_at"]:
            return None
        return self._admin_store.get_by_id(session["admin_id"])

    def logout(self, token: str) -> None:
        self._collection.delete_one({"token": token, "is_admin_session": True})
