from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class FollowerRepository(ABC):
    @abstractmethod
    def follow(self, user_id: str, masjid_id: str, notifications_enabled: bool) -> dict:
        pass

    @abstractmethod
    def unfollow(self, user_id: str, masjid_id: str) -> bool:
        pass

    @abstractmethod
    def is_following(self, user_id: str, masjid_id: str) -> bool:
        pass

    @abstractmethod
    def get_followers_count(self, masjid_id: str) -> int:
        pass

    @abstractmethod
    def get_follower_ids(self, masjid_id: str) -> List[str]:
        pass
