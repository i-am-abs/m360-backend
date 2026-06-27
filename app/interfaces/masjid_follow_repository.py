from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class MasjidFollowRepository(ABC):
    @abstractmethod
    def follow(self, user_id: str, masjid_id: str) -> None:
        """Record that a user follows a masjid (idempotent)."""

    @abstractmethod
    def unfollow(self, user_id: str, masjid_id: str) -> None:
        """Remove a follow relationship."""

    @abstractmethod
    def is_following(self, user_id: str, masjid_id: str) -> bool:
        """Return True when the user follows the masjid."""

    @abstractmethod
    def list_follower_user_ids(self, masjid_id: str) -> List[str]:
        """Return all user ids following a masjid."""
