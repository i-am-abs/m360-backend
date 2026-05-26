from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.exceptions.base import ApiException
from app.interfaces.user_repository import UserRepository
from app.utils.session_ttl import session_expires_in, session_never_expires


class JsonFileUserRepository(UserRepository):
    def __init__(self, filePath: str) -> None:
        if not filePath:
            raise ApiException(
                "USER_STORE_FILE is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
                code="CONFIG_MISSING",
            )
        self.filePath = filePath
        self.lock = RLock()
        self.bootstrap()

    def ensureUser(self, phoneNumber: str) -> Dict[str, Any]:
        with self.lock:
            data = self.readJsonFile()
            user = data["users_by_phone"].get(phoneNumber)
            if user is None:
                user = {
                    "user_id": str(uuid4()),
                    "phone_number": phoneNumber,
                    "created_at": self.getCurrentIsoTimestamp(),
                }
                data["users_by_phone"][phoneNumber] = user
                self.writeJsonFile(data)
            return user

    def createSession(self, userId: str, ttlSeconds: int) -> Dict[str, Any]:
        with self.lock:
            data = self.readJsonFile()
            token = str(uuid4())
            entry: Dict[str, Any] = {"user_id": userId}
            if not session_never_expires(ttlSeconds):
                expiresAt = datetime.now(timezone.utc) + timedelta(seconds=ttlSeconds)
                entry["expires_at"] = expiresAt.isoformat()
            data["sessions"][token] = entry
            self.writeJsonFile(data)
            return {"access_token": token, "expires_in": session_expires_in(ttlSeconds)}

    def getUserBySession(self, accessToken: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            data = self.readJsonFile()
            session = data["sessions"].get(accessToken)
            if not session:
                return None
            if not self.isSessionActive(session):
                data["sessions"].pop(accessToken, None)
                self.writeJsonFile(data)
                return None
            userId = session["user_id"]
            for user in data["users_by_phone"].values():
                if user.get("user_id") == userId:
                    return user
            return None

    def resolveSessionUserId(self, accessToken: str) -> Optional[str]:
        with self.lock:
            data = self.readJsonFile()
            session = data["sessions"].get(accessToken)
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
            data = self.readJsonFile()
            data["sessions"].pop(accessToken, None)
            self.writeJsonFile(data)
        return self.createSession(userId, ttlSeconds)

    def isSessionActive(self, session: Dict[str, Any]) -> bool:
        raw = session.get("expires_at")
        if not raw:
            return True
        expiresAt = datetime.fromisoformat(raw)
        return datetime.now(timezone.utc) < expiresAt

    def listFavorites(self, userId: str) -> List[str]:
        with self.lock:
            data = self.readJsonFile()
            return list(data["favorites_by_user_id"].get(userId, []))

    def addFavorite(self, userId: str, placeId: str) -> List[str]:
        with self.lock:
            data = self.readJsonFile()
            favorites = data["favorites_by_user_id"].setdefault(userId, [])
            if placeId not in favorites:
                favorites.append(placeId)
                self.writeJsonFile(data)
            return list(favorites)

    def removeFavorite(self, userId: str, placeId: str) -> List[str]:
        with self.lock:
            data = self.readJsonFile()
            favorites = data["favorites_by_user_id"].setdefault(userId, [])
            data["favorites_by_user_id"][userId] = [
                pid for pid in favorites if pid != placeId
            ]
            self.writeJsonFile(data)
            return list(data["favorites_by_user_id"][userId])

    def getCurrentIsoTimestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def bootstrap(self) -> None:
        with self.lock:
            parent = os.path.dirname(self.filePath)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if not os.path.exists(self.filePath):
                self.writeJsonFile({
                    "users_by_phone": {},
                    "favorites_by_user_id": {},
                    "sessions": {},
                })

    def readJsonFile(self) -> Dict[str, Any]:
        with open(self.filePath, "r", encoding="utf-8") as f:
            return json.load(f)

    def writeJsonFile(self, payload: Dict[str, Any]) -> None:
        with open(self.filePath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)
