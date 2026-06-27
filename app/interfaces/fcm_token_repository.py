from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class FcmTokenRepository(ABC):
    @abstractmethod
    def register(self, user_id: str, token: str, platform: str | None = None) -> None:
        """Create or update an FCM device token for a user."""

    @abstractmethod
    def list_tokens_for_users(self, user_ids: List[str]) -> List[str]:
        """Return all device tokens belonging to the given users."""

    @abstractmethod
    def remove(self, token: str) -> None:
        """Remove a token (e.g. after FCM reports it invalid)."""
