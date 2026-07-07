from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class UserRepository(ABC):
    @abstractmethod
    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def resolve_session_user_id(self, access_token: str) -> Optional[str]:
        pass

    @abstractmethod
    def refresh_session(self, access_token: str, ttl_seconds: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_favorites(self, user_id: str) -> List[str]:
        pass

    @abstractmethod
    def add_favorite(self, user_id: str, place_id: str) -> List[str]:
        pass

    @abstractmethod
    def remove_favorite(self, user_id: str, place_id: str) -> List[str]:
        pass

    @abstractmethod
    def block_user(self, user_id: str) -> None:
        ...

    @abstractmethod
    def unblock_user(self, user_id: str) -> None:
        ...

    @abstractmethod
    def list_users(self, skip: int, limit: int) -> Dict[str, Any]:
        ...

    @abstractmethod
    def search_users(self, query: str) -> List[Dict[str, Any]]:
        ...
