from __future__ import annotations

from typing import Dict, List, Tuple

from app.interfaces.notification_sender import NotificationSender
from app.utils.structured_log import log_event

# FCM multicast accepts at most 500 tokens per request.
_FCM_BATCH_SIZE = 500


class FcmNotificationSender(NotificationSender):
    """Sends push notifications via Firebase Cloud Messaging.

    firebase-admin is imported lazily so the app can boot without the package
    or credentials when FCM is disabled.
    """

    def __init__(self, credentials_file: str) -> None:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:  # type: ignore[attr-defined]
            cred = credentials.Certificate(credentials_file)
            firebase_admin.initialize_app(cred)
        # Cache the messaging module for reuse.
        from firebase_admin import messaging

        self._messaging = messaging

    def send_to_tokens(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, str] | None = None,
    ) -> Tuple[int, int, List[str]]:
        unique_tokens = list(dict.fromkeys(t for t in tokens if t))
        if not unique_tokens:
            return 0, 0, []

        sent = 0
        failed = 0
        invalid: List[str] = []

        for start in range(0, len(unique_tokens), _FCM_BATCH_SIZE):
            batch = unique_tokens[start:start + _FCM_BATCH_SIZE]
            message = self._messaging.MulticastMessage(
                tokens=batch,
                notification=self._messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
            )
            response = self._messaging.send_each_for_multicast(message)
            sent += response.success_count
            failed += response.failure_count
            invalid.extend(self._collect_invalid(batch, response))

        log_event(
            "fcm",
            "multicast_sent",
            recipients=len(unique_tokens),
            sent=sent,
            failed=failed,
            invalid=len(invalid),
        )
        return sent, failed, invalid

    def _collect_invalid(self, batch: List[str], response) -> List[str]:
        invalid: List[str] = []
        for token, result in zip(batch, response.responses):
            if result.success:
                continue
            error = getattr(result, "exception", None)
            error_name = type(error).__name__ if error else ""
            if error_name in {"UnregisteredError", "SenderIdMismatchError", "InvalidArgumentError"}:
                invalid.append(token)
        return invalid


class StubNotificationSender(NotificationSender):
    """No-op sender used when FCM is not configured (logs only)."""

    def send_to_tokens(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, str] | None = None,
    ) -> Tuple[int, int, List[str]]:
        unique = [t for t in tokens if t]
        log_event(
            "fcm",
            "stub_send",
            level="warning",
            recipients=len(unique),
            title=title,
        )
        return len(unique), 0, []
