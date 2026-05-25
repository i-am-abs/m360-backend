from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.interfaces.user_repository import UserRepository
from app.utils.session_ttl import session_expires_in, session_never_expires


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.lock = RLock()
        self.data: Dict[str, Any] = {
            "users_by_phone": {},
            "favorites_by_user_id": {},
            "sessions": {},
        }

    def ensureUser(self, phoneNumber: str) -> Dict[str, Any]:
        with self.lock:
            user = self.data["users_by_phone"].get(phoneNumber)
            if user is None:
                user = {
                    "user_id": str(uuid4()),
                    "phone_number": phoneNumber,
                    "created_at": self.getCurrentIsoTimestamp(),
                }
                self.data["users_by_phone"][phoneNumber] = user
            return user

    def createSession(self, userId: str, ttlSeconds: int) -> Dict[str, Any]:
        with self.lock:
            token = str(uuid4())
            entry: Dict[str, Any] = {"user_id": userId}
            if not session_never_expires(ttlSeconds):
                expiresAt = datetime.now(timezone.utc) + timedelta(seconds=ttlSeconds)
                entry["expires_at"] = expiresAt.isoformat()
            self.data["sessions"][token] = entry
            return {"access_token": token, "expires_in": session_expires_in(ttlSeconds)}

    def getUserBySession(self, accessToken: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            session = self.data["sessions"].get(accessToken)
            if not session:
                return None
            if not self.isSessionActive(session):
                self.data["sessions"].pop(accessToken, None)
                return None
            userId = session["user_id"]
            for user in self.data["users_by_phone"].values():
                if user.get("user_id") == userId:
                    return user
            return None

    def resolveSessionUserId(self, accessToken: str) -> Optional[str]:
        with self.lock:
            session = self.data["sessions"].get(accessToken)
            if not session:
                return None
            userId = session.get("user_id")
            return str(userId) if userId else None

    def refreshSession(self, accessToken: str, ttlSeconds: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            userId = self.resolveSessionUserId(accessToken)
            if not userId:
                return None
            if session_never_expires(ttlSeconds):
                return {
                    "access_token": accessToken,
                    "expires_in": session_expires_in(ttlSeconds),
                }
            self.data["sessions"].pop(accessToken, None)
        return self.createSession(userId, ttlSeconds)

    def isSessionActive(self, session: Dict[str, Any]) -> bool:
        raw = session.get("expires_at")
        if not raw:
            return True
        expiresAt = datetime.fromisoformat(raw)
        return datetime.now(timezone.utc) < expiresAt

    def listFavorites(self, userId: str) -> List[str]:
        with self.lock:
            return list(self.data["favorites_by_user_id"].get(userId, []))

    def addFavorite(self, userId: str, placeId: str) -> List[str]:
        with self.lock:
            favorites = self.data["favorites_by_user_id"].setdefault(userId, [])
            if placeId not in favorites:
                favorites.append(placeId)
            return list(favorites)

    def removeFavorite(self, userId: str, placeId: str) -> List[str]:
        with self.lock:
            favorites = self.data["favorites_by_user_id"].setdefault(userId, [])
            self.data["favorites_by_user_id"][userId] = [
                pid for pid in favorites if pid != placeId
            ]
            return list(self.data["favorites_by_user_id"][userId])

    def getCurrentIsoTimestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
