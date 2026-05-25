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
        self.redisClient = client
        self.keyPrefix = (settings.redis_key_prefix or "m360").strip() or "m360"

    def buildPhoneKey(self, phoneNumber: str) -> str:
        return f"{self.keyPrefix}:user:phone:{phoneNumber}"

    def buildUserIdKey(self, userId: str) -> str:
        return f"{self.keyPrefix}:user:id:{userId}"

    def buildSessionKey(self, accessToken: str) -> str:
        return f"{self.keyPrefix}:session:{accessToken}"

    def buildFavoritesKey(self, userId: str) -> str:
        return f"{self.keyPrefix}:favorites:{userId}"

    def ensureUser(self, phoneNumber: str) -> Dict[str, Any]:
        rawUserPayload = self.redisClient.get(self.buildPhoneKey(phoneNumber))
        if rawUserPayload:
            return json.loads(rawUserPayload)
        user = {
            "user_id": str(uuid4()),
            "phone_number": phoneNumber,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        serializedUser = json.dumps(user)
        self.redisClient.set(self.buildPhoneKey(phoneNumber), serializedUser)
        self.redisClient.set(self.buildUserIdKey(user["user_id"]), serializedUser)
        return user

    def createSession(self, userId: str, ttlSeconds: int) -> Dict[str, Any]:
        accessToken = str(uuid4())
        sessionKey = self.buildSessionKey(accessToken)
        if session_never_expires(ttlSeconds):
            self.redisClient.set(sessionKey, userId)
        else:
            self.redisClient.setex(sessionKey, ttlSeconds, userId)
        return {"access_token": accessToken, "expires_in": session_expires_in(ttlSeconds)}

    def getUserBySession(self, accessToken: str) -> Optional[Dict[str, Any]]:
        userId = self.redisClient.get(self.buildSessionKey(accessToken))
        if not userId:
            return None
        rawUserPayload = self.redisClient.get(self.buildUserIdKey(userId))
        if not rawUserPayload:
            return None
        return json.loads(rawUserPayload)

    def resolveSessionUserId(self, accessToken: str) -> Optional[str]:
        userId = self.redisClient.get(self.buildSessionKey(accessToken))
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
        self.redisClient.delete(self.buildSessionKey(accessToken))
        return self.createSession(userId, ttlSeconds)

    def listFavorites(self, userId: str) -> List[str]:
        rawFavoritesPayload = self.redisClient.get(self.buildFavoritesKey(userId))
        if not rawFavoritesPayload:
            return []
        favoritesData = json.loads(rawFavoritesPayload)
        return list(favoritesData) if isinstance(favoritesData, list) else []

    def addFavorite(self, userId: str, placeId: str) -> List[str]:
        favoritePlaceIds = self.listFavorites(userId)
        if placeId not in favoritePlaceIds:
            favoritePlaceIds.append(placeId)
        self.redisClient.set(self.buildFavoritesKey(userId), json.dumps(favoritePlaceIds))
        return list(favoritePlaceIds)

    def removeFavorite(self, userId: str, placeId: str) -> List[str]:
        favoritePlaceIds = [place for place in self.listFavorites(userId) if place != placeId]
        self.redisClient.set(self.buildFavoritesKey(userId), json.dumps(favoritePlaceIds))
        return favoritePlaceIds
