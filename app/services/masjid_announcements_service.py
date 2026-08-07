from __future__ import annotations

from typing import Any, Dict

from app.core.enums.role import UserRole
from app.interfaces.audit_log_repository import AuditLogRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.schemas.masjid_content import MasjidAnnouncementsEnabledRequest
from app.services.rbac_service import RbacService
from app.utils.structured_log import log_event, log_timing


class MasjidAnnouncementsService:
    def __init__(
            self,
            masjid_store: MasjidRepository,
            audit_store: AuditLogRepository,
            rbac: RbacService,
    ) -> None:
        self._masjid_store = masjid_store
        self._audit_store = audit_store
        self._rbac = rbac

    def set_announcements_enabled(
            self,
            place_id: str,
            body: MasjidAnnouncementsEnabledRequest,
            current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        user = self._rbac.require_roles(
            current_user,
            {UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value},
        )

        with log_timing(
                "masjid_announcements",
                "set_enabled",
                resource_id=place_id,
        ):
            stored = self._masjid_store.set_announcements_enabled(
                place_id,
                body.enabled,
                updated_by=str(user.get("user_id") or ""),
            )

        self._audit_store.write({
            "action": "masjid_announcements_enabled_updated",
            "resource_type": "masjid_announcements",
            "resource_id": place_id,
            "user_id": user.get("user_id"),
            "details": {"enabled": body.enabled},
        })
        log_event(
            "masjid_announcements",
            "set_enabled",
            user_id=user.get("user_id"),
            resource_id=place_id,
            enabled=body.enabled,
        )
        return stored
