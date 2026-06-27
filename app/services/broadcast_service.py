from __future__ import annotations

from typing import Any, Dict, Optional

from app.interfaces.audit_log_repository import AuditLogRepository
from app.interfaces.broadcast_repository import BroadcastRepository
from app.schemas.broadcast import (
    BroadcastCreateRequest,
    BroadcastDeliveryResult,
    BroadcastItem,
    BroadcastPage,
)
from app.services.notification_service import NotificationService
from app.services.rbac_service import RbacService
from app.utils.structured_log import log_event, log_timing


class BroadcastService:
    """Masjid broadcast feed: admins create messages, users read them."""

    def __init__(
        self,
        broadcast_store: BroadcastRepository,
        notification_service: NotificationService,
        audit_store: AuditLogRepository,
        rbac: RbacService,
        default_page_size: int = 20,
    ) -> None:
        self._broadcast_store = broadcast_store
        self._notifications = notification_service
        self._audit_store = audit_store
        self._rbac = rbac
        self._default_page_size = default_page_size

    def create_broadcast(
        self,
        place_id: str,
        body: BroadcastCreateRequest,
        current_user: Dict[str, Any],
    ) -> BroadcastDeliveryResult:
        user = self._rbac.require_masjid_admin(current_user, place_id)

        with log_timing("broadcast", "create", resource_id=place_id):
            stored = self._broadcast_store.create({
                "masjid_id": place_id,
                "caption": body.caption,
                "video_uri": body.video_uri,
                "thumbnail_uri": body.thumbnail_uri,
                "message_type": body.message_type,
                "created_by": str(user.get("user_id") or ""),
            })

        self._audit_store.write({
            "action": "broadcast_created",
            "resource_type": "broadcast",
            "resource_id": stored["broadcast_id"],
            "user_id": user.get("user_id"),
            "details": {"masjid_id": place_id, "message_type": body.message_type},
        })

        recipients, sent, failed = self._notifications.notify_followers(
            place_id,
            title="New masjid update",
            body=body.caption[:120],
            data={
                "broadcast_id": stored["broadcast_id"],
                "masjid_id": place_id,
                "message_type": body.message_type,
            },
        )
        log_event(
            "broadcast",
            "created",
            resource_id=stored["broadcast_id"],
            user_id=user.get("user_id"),
            recipients=recipients,
        )
        return BroadcastDeliveryResult(
            broadcast_id=stored["broadcast_id"],
            recipients=recipients,
            sent=sent,
            failed=failed,
        )

    def list_broadcasts(
        self,
        place_id: str,
        *,
        limit: Optional[int] = None,
        before_id: Optional[int] = None,
    ) -> BroadcastPage:
        page_size = self._clamp_limit(limit)
        items, has_more = self._broadcast_store.list_by_masjid(
            place_id,
            limit=page_size,
            before_seq=before_id,
        )
        models = [self._to_item(doc) for doc in items]
        next_cursor = models[-1].seq if (models and has_more) else None
        log_event(
            "broadcast",
            "listed",
            resource_id=place_id,
            count=len(models),
            has_more=has_more,
        )
        return BroadcastPage(items=models, next_cursor=next_cursor, has_more=has_more)

    def notify_followers_internal(
        self,
        place_id: str,
        broadcast_id: str,
    ) -> BroadcastDeliveryResult:
        doc = self._broadcast_store.get_by_id(broadcast_id)
        caption = (doc or {}).get("caption", "New masjid update")
        recipients, sent, failed = self._notifications.notify_followers(
            place_id,
            title="New masjid update",
            body=caption[:120],
            data={"broadcast_id": broadcast_id, "masjid_id": place_id},
        )
        return BroadcastDeliveryResult(
            broadcast_id=broadcast_id,
            recipients=recipients,
            sent=sent,
            failed=failed,
        )

    def _clamp_limit(self, limit: Optional[int]) -> int:
        if limit is None:
            return self._default_page_size
        return max(1, min(100, limit))

    @staticmethod
    def _to_item(doc: Dict[str, Any]) -> BroadcastItem:
        return BroadcastItem(
            id=doc["broadcast_id"],
            masjid_id=doc["masjid_id"],
            caption=doc["caption"],
            video_uri=doc.get("video_uri"),
            thumbnail_uri=doc.get("thumbnail_uri"),
            message_type=doc.get("message_type", "text"),
            seq=int(doc.get("seq", 0)),
            created_at=doc.get("created_at", ""),
            created_by=doc.get("created_by"),
        )
