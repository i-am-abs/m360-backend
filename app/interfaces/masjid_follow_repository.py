from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class MasjidFollowRepository(ABC):
    @abstractmethod
    def follow(self, user_id: str, masjid_id: str) -> None:
        pass

    @abstractmethod
    def unfollow(self, user_id: str, masjid_id: str) -> None:
        pass

    @abstractmethod
    def is_following(self, user_id: str, masjid_id: str) -> bool:
        pass

    @abstractmethod
    def list_follower_user_ids(self, masjid_id: str) -> List[str]:
        pass
