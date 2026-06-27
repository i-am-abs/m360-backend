from __future__ import annotations

from typing import Any, Dict, List

from app.interfaces.audit_log_repository import AuditLogRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.schemas.masjid_content import MasjidTimingsRequest, PrayerTimingItem
from app.services.rbac_service import RbacService
from app.utils.structured_log import log_event, log_timing


class MasjidTimingsService:
    def __init__(
            self,
            masjid_store: MasjidRepository,
            audit_store: AuditLogRepository,
            rbac: RbacService,
    ) -> None:
        self._masjid_store = masjid_store
        self._audit_store = audit_store
        self._rbac = rbac

    def create_timings(
            self,
            place_id: str,
            body: MasjidTimingsRequest,
            current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._save_timings(place_id, body, current_user, action="timings_created")

    def update_timings(
            self,
            place_id: str,
            body: MasjidTimingsRequest,
            current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._save_timings(place_id, body, current_user, action="timings_updated")

    def _save_timings(
            self,
            place_id: str,
            body: MasjidTimingsRequest,
            current_user: Dict[str, Any],
            *,
            action: str,
    ) -> Dict[str, Any]:
        user = self._rbac.require_masjid_admin(current_user, place_id)
        timings = [item.model_dump() for item in body.timings]

        with log_timing("masjid_timings", action, resource_id=place_id):
            stored = self._masjid_store.update_timings(
                place_id,
                timings,
                updated_by=str(user.get("user_id") or ""),
            )

        self._audit_store.write({
            "action": action,
            "resource_type": "masjid_timings",
            "resource_id": place_id,
            "user_id": user.get("user_id"),
            "details": {"count": len(timings)},
        })
        log_event(
            "masjid_timings",
            action,
            user_id=user.get("user_id"),
            resource_id=place_id,
        )
        return {"place_id": place_id, "timings": stored.get("timings", timings)}

    def get_timings(self, place_id: str) -> List[PrayerTimingItem]:
        raw = self._masjid_store.get_timings(place_id) or []
        return [PrayerTimingItem(**item) for item in raw]
