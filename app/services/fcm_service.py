from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

log = get_logger(__name__)


class FcmService:
    def __init__(self, user_store=None, db=None):
        self._user_store = user_store
        self._db = db

    def send_to_user(self, user_id: str, title: str, body: str, data: Dict[str, str]) -> None:
        tokens = self._get_user_tokens(user_id)
        if not tokens:
            log.info("No FCM tokens for user %s", user_id)
            return
        for token in tokens:
            try:
                self._send(token, title, body, data)
            except Exception as e:
                log.warning("FCM send failed for user %s token %s: %s", user_id, token[:16], e)

    def send_to_topic(self, topic: str, title: str, body: str, data: Dict[str, str]) -> None:
        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in data.items()},
                topic=topic,
            )
            messaging.send(message)
            log.info("FCM topic sent to %s", topic)
        except Exception as e:
            log.warning("FCM topic send failed for %s: %s", topic, e)

    def store_token(self, user_id: str, token: str) -> None:
        if self._db is None:
            return
        self._db["users"].update_one(
            {"user_id": user_id},
            {"$addToSet": {"fcm_tokens": token}},
        )
        log.info("FCM token stored for user %s", user_id)

    def _get_user_tokens(self, user_id: str) -> List[str]:
        if self._db is None:
            return []
        doc = self._db["users"].find_one({"user_id": user_id}, {"fcm_tokens": 1})
        if doc:
            return doc.get("fcm_tokens", [])
        return []

    def _send(self, token: str, title: str, body: str, data: Dict[str, str]) -> None:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in data.items()},
            token=token,
        )
        messaging.send(message)
