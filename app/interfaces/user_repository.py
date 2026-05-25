from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class UserRepository(ABC):
    @abstractmethod
    def ensureUser(self, phoneNumber: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def createSession(self, userId: str, ttlSeconds: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    def getUserBySession(self, accessToken: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def resolveSessionUserId(self, accessToken: str) -> Optional[str]:
        pass

    @abstractmethod
    def refreshSession(self, accessToken: str, ttlSeconds: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def listFavorites(self, userId: str) -> List[str]:
        pass

    @abstractmethod
    def addFavorite(self, userId: str, placeId: str) -> List[str]:
        pass

    @abstractmethod
    def removeFavorite(self, userId: str, placeId: str) -> List[str]:
        pass
