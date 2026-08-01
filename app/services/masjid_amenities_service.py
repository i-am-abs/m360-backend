from __future__ import annotations

from typing import Any, Dict

from app.interfaces.audit_log_repository import AuditLogRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.schemas.masjid_content import MasjidAmenitiesRequest
from app.services.rbac_service import RbacService
from app.utils.structured_log import log_event, log_timing


class MasjidAmenitiesService:
    def __init__(
            self,
            masjid_store: MasjidRepository,
            audit_store: AuditLogRepository,
            rbac: RbacService,
    ) -> None:
        self._masjid_store = masjid_store
        self._audit_store = audit_store
        self._rbac = rbac

    def create_amenities(
            self,
            place_id: str,
            body: MasjidAmenitiesRequest,
            current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._save(place_id, body, current_user, action="amenities_created")

    def update_amenities(
            self,
            place_id: str,
            body: MasjidAmenitiesRequest,
            current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._save(place_id, body, current_user, action="amenities_updated")

    def _save(
            self,
            place_id: str,
            body: MasjidAmenitiesRequest,
            current_user: Dict[str, Any],
            *,
            action: str,
    ) -> Dict[str, Any]:
        user = self._rbac.require_masjid_admin(current_user, place_id)

        with log_timing("masjid_amenities", action, resource_id=place_id):
            stored = self._masjid_store.update_amenities(
                place_id,
                body.amenities,
                updated_by=str(user.get("user_id") or ""),
            )

        self._audit_store.write({
            "action": action,
            "resource_type": "masjid_amenities",
            "resource_id": place_id,
            "user_id": user.get("user_id"),
            "details": {"amenities": body.amenities},
        })
        log_event(
            "masjid_amenities",
            action,
            user_id=user.get("user_id"),
            resource_id=place_id,
        )
        return {"place_id": place_id, "amenities": stored.get("amenities", body.amenities)}
