from __future__ import annotations

from http import HTTPStatus
from typing import Dict, List

from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.follower_repository import FollowerRepository

log = get_logger(__name__)


class FollowerService:
    def __init__(self, follower_repo: FollowerRepository) -> None:
        self._repo = follower_repo

    def follow(self, user_id: str, masjid_id: str, notifications_enabled: bool = True) -> Dict[str, int]:
        if self._repo.is_following(user_id, masjid_id):
            raise ApiException(
                "Already following this masjid",
                status_code=HTTPStatus.BAD_REQUEST,
            )
        result = self._repo.follow(user_id, masjid_id, notifications_enabled)
        count = self._repo.get_followers_count(masjid_id)
        log.info("User %s followed masjid %s", user_id, masjid_id)
        return {"follower_count": count}

    def unfollow(self, user_id: str, masjid_id: str) -> Dict[str, int]:
        if not self._repo.is_following(user_id, masjid_id):
            raise ApiException(
                "Not following this masjid",
                status_code=HTTPStatus.BAD_REQUEST,
            )
        self._repo.unfollow(user_id, masjid_id)
        count = self._repo.get_followers_count(masjid_id)
        log.info("User %s unfollowed masjid %s", user_id, masjid_id)
        return {"follower_count": count}

    def is_following(self, user_id: str, masjid_id: str) -> bool:
        return self._repo.is_following(user_id, masjid_id)

    def get_followers_count(self, masjid_id: str) -> int:
        return self._repo.get_followers_count(masjid_id)

    def get_follower_ids(self, masjid_id: str) -> List[str]:
        return self._repo.get_follower_ids(masjid_id)