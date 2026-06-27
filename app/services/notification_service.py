from __future__ import annotations

from typing import Dict, Tuple

from app.interfaces.fcm_token_repository import FcmTokenRepository
from app.interfaces.masjid_follow_repository import MasjidFollowRepository
from app.interfaces.notification_sender import NotificationSender
from app.utils.structured_log import log_event, log_timing


class NotificationService:
    """Owns device-token registration, masjid follows, and fan-out delivery."""

    def __init__(
        self,
        token_store: FcmTokenRepository,
        follow_store: MasjidFollowRepository,
        sender: NotificationSender,
    ) -> None:
        self._token_store = token_store
        self._follow_store = follow_store
        self._sender = sender

    def register_token(self, user_id: str, token: str, platform: str | None = None) -> None:
        self._token_store.register(user_id, token, platform)
        log_event("fcm", "token_registered", user_id=user_id, platform=platform)

    def follow_masjid(self, user_id: str, masjid_id: str) -> None:
        self._follow_store.follow(user_id, masjid_id)
        log_event("broadcast", "masjid_followed", user_id=user_id, resource_id=masjid_id)

    def unfollow_masjid(self, user_id: str, masjid_id: str) -> None:
        self._follow_store.unfollow(user_id, masjid_id)
        log_event("broadcast", "masjid_unfollowed", user_id=user_id, resource_id=masjid_id)

    def is_following(self, user_id: str, masjid_id: str) -> bool:
        return self._follow_store.is_following(user_id, masjid_id)

    def notify_followers(
        self,
        masjid_id: str,
        title: str,
        body: str,
        data: Dict[str, str] | None = None,
    ) -> Tuple[int, int, int]:
        """Fan a notification out to every follower of a masjid.

        Returns ``(recipients, sent, failed)``. Best-effort: failures are logged
        and invalid tokens pruned, never raised to the caller.
        """
        with log_timing("broadcast", "fanout", resource_id=masjid_id):
            user_ids = self._follow_store.list_follower_user_ids(masjid_id)
            tokens = self._token_store.list_tokens_for_users(user_ids)
            if not tokens:
                log_event("broadcast", "no_recipients", resource_id=masjid_id)
                return 0, 0, 0

            sent, failed, invalid = self._sender.send_to_tokens(tokens, title, body, data)
            for bad_token in invalid:
                self._token_store.remove(bad_token)

        log_event(
            "broadcast",
            "fanout_complete",
            resource_id=masjid_id,
            recipients=len(tokens),
            sent=sent,
            failed=failed,
        )
        return len(tokens), sent, failed
