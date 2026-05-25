from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.interfaces.user_repository import UserRepository
from app.utils.session_ttl import session_expires_in, session_never_expires


class MongoUserStore(UserRepository):
    def __init__(self, db: Database) -> None:
        self.database = db
        self.usersCollection = db["users"]
        self.sessionsCollection = db["sessions"]
        self.favoritesCollection = db["favorites"]
        self.ensureIndexes()

    def ensureIndexes(self) -> None:
        self.usersCollection.create_index([("phone_number", ASCENDING)], unique=True)
        self.usersCollection.create_index([("user_id", ASCENDING)], unique=True)
        self.sessionsCollection.create_index([("access_token", ASCENDING)], unique=True)
        self.sessionsCollection.create_index("expires_at", expireAfterSeconds=0)
        self.favoritesCollection.create_index([("user_id", ASCENDING)], unique=True)

    def ensureUser(self, phoneNumber: str) -> Dict[str, Any]:
        document = self.usersCollection.find_one({"phone_number": phoneNumber})
        if document:
            return self.asUserDictionary(document)
        userId = str(uuid4())
        payload = {
            "user_id": userId,
            "phone_number": phoneNumber,
            "created_at": self.nowIsoTimestamp(),
        }
        try:
            self.usersCollection.insert_one(payload)
        except DuplicateKeyError:
            document = self.usersCollection.find_one({"phone_number": phoneNumber})
            if document:
                return self.asUserDictionary(document)
            raise
        return payload

    def createSession(self, userId: str, ttlSeconds: int) -> Dict[str, Any]:
        accessToken = str(uuid4())
        payload: Dict[str, Any] = {
            "access_token": accessToken,
            "user_id": userId,
        }
        if not session_never_expires(ttlSeconds):
            payload["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=ttlSeconds)
        self.sessionsCollection.insert_one(payload)
        return {"access_token": accessToken, "expires_in": session_expires_in(ttlSeconds)}

    def getUserBySession(self, accessToken: str) -> Optional[Dict[str, Any]]:
        sessionDocument = self.sessionsCollection.find_one({"access_token": accessToken})
        if not sessionDocument:
            return None
        if not self.isSessionActive(sessionDocument):
            self.sessionsCollection.delete_one({"access_token": accessToken})
            return None
        userId = sessionDocument.get("user_id")
        if not userId:
            return None
        userDocument = self.usersCollection.find_one({"user_id": userId})
        return self.asUserDictionary(userDocument) if userDocument else None

    def resolveSessionUserId(self, accessToken: str) -> Optional[str]:
        sessionDocument = self.sessionsCollection.find_one({"access_token": accessToken})
        if not sessionDocument:
            return None
        userId = sessionDocument.get("user_id")
        return str(userId) if userId else None

    def refreshSession(self, accessToken: str, ttlSeconds: int) -> Optional[Dict[str, Any]]:
        userId = self.resolveSessionUserId(accessToken)
        if not userId:
            return None
        if session_never_expires(ttlSeconds):
            return {
                "access_token": accessToken,
                "expires_in": session_expires_in(ttlSeconds),
            }
        self.sessionsCollection.delete_one({"access_token": accessToken})
        return self.createSession(userId, ttlSeconds)

    def isSessionActive(self, sessionDocument: Dict[str, Any]) -> bool:
        expiresAt = sessionDocument.get("expires_at")
        if expiresAt is None:
            return True
        if not isinstance(expiresAt, datetime):
            return True
        return expiresAt > datetime.now(timezone.utc)

    def listFavorites(self, userId: str) -> List[str]:
        favoritesDocument = self.favoritesCollection.find_one({"user_id": userId})
        if not favoritesDocument:
            return []
        return list(favoritesDocument.get("place_ids") or [])

    def addFavorite(self, userId: str, placeId: str) -> List[str]:
        self.favoritesCollection.update_one(
            {"user_id": userId},
            {"$addToSet": {"place_ids": placeId}, "$setOnInsert": {"user_id": userId}},
            upsert=True,
        )
        return self.listFavorites(userId)

    def removeFavorite(self, userId: str, placeId: str) -> List[str]:
        self.favoritesCollection.update_one(
            {"user_id": userId},
            {"$pull": {"place_ids": placeId}},
        )
        return self.listFavorites(userId)

    @staticmethod
    def nowIsoTimestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def asUserDictionary(userDocument: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_id": userDocument["user_id"],
            "phone_number": userDocument["phone_number"],
            "created_at": userDocument["created_at"],
        }
