from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Optional

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.committee_designation import CommitteeDesignation
from app.core.enums.error_code import ErrorCode
from app.core.enums.role import UserRole
from app.exceptions.base import ApiException
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.audit_log_repository import AuditLogRepository
from app.interfaces.masjid_listing_repository import MasjidListingRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.schemas.admin import AdminRegisterRequest, AdminResponse, AdminStatusUpdateRequest
from app.services.rbac_service import RbacService
from app.utils.admin_link import committee_member_from_admin
from app.utils.phone import canonicalize_india_phone
from app.utils.structured_log import log_event, log_timing


class AdminService:
    def __init__(
            self,
            admin_store: AdminRepository,
            audit_store: AuditLogRepository,
            rbac: RbacService,
            masjid_store: Optional[MasjidRepository] = None,
            listing_store: Optional[MasjidListingRepository] = None,
    ) -> None:
        self._admin_store = admin_store
        self._audit_store = audit_store
        self._rbac = rbac
        self._masjid_store = masjid_store
        self._listing_store = listing_store

    def register(
            self,
            request: AdminRegisterRequest,
            *,
            current_user: Optional[Dict[str, Any]] = None,
    ) -> AdminResponse:
        try:
            phone = canonicalize_india_phone(request.phone)
        except ValueError as exc:
            raise ApiException(
                str(exc),
                status_code=HTTPStatus.BAD_REQUEST.value,
                code=ErrorCode.INVALID_PHONE,
            ) from exc

        system_role = request.system_role
        designation = request.resolved_designation

        with log_timing("admin", "register", phone=phone):
            if system_role == UserRole.SUPER_ADMIN.value:
                if not current_user:
                    raise ApiException(
                        "Super admin registration requires authentication",
                        status_code=HTTPStatus.FORBIDDEN.value,
                        code=ErrorCode.FORBIDDEN,
                    )
                self._rbac.require_roles(current_user, {UserRole.SUPER_ADMIN.value})

            user_id = current_user.get("user_id") if current_user else None
            existing = self._admin_store.get_by_phone(phone)
            if existing:
                stored = self._handle_existing_admin(
                    existing,
                    request,
                    phone=phone,
                    user_id=str(user_id) if user_id else None,
                    system_role=system_role,
                    designation=designation,
                )
            else:
                try:
                    stored = self._admin_store.create({
                        "user_id": user_id,
                        "name": request.name,
                        "phone": phone,
                        "profile_image": request.profile_image,
                        "role": system_role,
                        "designation": designation,
                        "committee_id": request.committee_id,
                        "masjid_place_id": request.masjid_place_id,
                        "status": AdminRegistrationStatus.PENDING.value,
                    })
                except ValueError as exc:
                    raise ApiException(
                        str(exc),
                        status_code=HTTPStatus.CONFLICT.value,
                        code=ErrorCode.VALIDATION_ERROR,
                    ) from exc

        self._audit_store.write({
            "action": "admin_registered",
            "resource_type": "admin",
            "resource_id": stored["admin_id"],
            "user_id": user_id,
            "details": {
                "phone": phone,
                "role": stored.get("role"),
                "designation": stored.get("designation"),
                "masjid_place_id": stored.get("masjid_place_id"),
            },
        })
        log_event(
            "admin",
            "registered",
            resource_id=stored["admin_id"],
            user_id=user_id,
        )
        return self._to_response(stored)

    def _handle_existing_admin(
            self,
            existing: Dict[str, Any],
            request: AdminRegisterRequest,
            *,
            phone: str,
            user_id: Optional[str],
            system_role: str,
            designation: str,
    ) -> Dict[str, Any]:
        """Reuse existing admin row when registering a masjid committee assignment."""
        admin_id = str(existing["admin_id"])
        fields: Dict[str, Any] = {}

        if user_id and existing.get("user_id") != user_id:
            fields["user_id"] = user_id

        if existing.get("phone") != phone:
            fields["phone"] = phone

        if request.masjid_place_id:
            existing_place = existing.get("masjid_place_id")
            if existing_place and existing_place != request.masjid_place_id:
                raise ApiException(
                    "This phone number is already an admin for another masjid. "
                    "Contact a super admin to change the assignment.",
                    status_code=HTTPStatus.CONFLICT.value,
                    code=ErrorCode.VALIDATION_ERROR,
                )
            if not existing_place:
                fields["masjid_place_id"] = request.masjid_place_id
                if existing.get("role") != UserRole.SUPER_ADMIN.value:
                    fields["status"] = AdminRegistrationStatus.PENDING.value
            if request.name:
                fields["name"] = request.name
            if request.profile_image is not None:
                fields["profile_image"] = request.profile_image
            if request.committee_id is not None:
                fields["committee_id"] = request.committee_id
            if (
                    existing.get("role") not in UserRole.admin_roles()
                    and system_role in UserRole.admin_roles()
            ):
                fields["role"] = system_role
            if designation:
                fields["designation"] = designation

            if fields:
                updated = self._admin_store.update_fields(admin_id, fields)
                return updated or existing
            return existing

        raise ApiException(
            "This phone number is already an admin",
            status_code=HTTPStatus.CONFLICT.value,
            code=ErrorCode.VALIDATION_ERROR,
        )

    def list_admins(
            self,
            current_user: Dict[str, Any],
            *,
            status: Optional[str] = None,
    ) -> List[AdminResponse]:
        self._rbac.require_roles(
            current_user,
            {UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value},
        )
        docs = self._admin_store.list_all(status=status)
        return [self._to_response(doc) for doc in docs]

    def update_status(
            self,
            admin_id: str,
            body: AdminStatusUpdateRequest,
            current_user: Dict[str, Any],
    ) -> AdminResponse:
        self._rbac.require_roles(current_user, {UserRole.SUPER_ADMIN.value})

        stored = self._admin_store.update_status(
            admin_id,
            body.status.value,
            updated_by=str(current_user.get("user_id") or ""),
        )
        if not stored:
            raise ApiException(
                "Admin registration not found",
                status_code=HTTPStatus.NOT_FOUND.value,
                code=ErrorCode.NOT_FOUND,
            )

        if (
                body.status == AdminRegistrationStatus.APPROVED
                and stored.get("masjid_place_id")
        ):
            place_id = str(stored["masjid_place_id"])
            if self._masjid_store is not None:
                approved = self._admin_store.list_approved_for_place(place_id)
                # Ensure the just-approved doc is included even if read is eventually consistent.
                if not any(d.get("admin_id") == stored.get("admin_id") for d in approved):
                    approved = [stored] + approved
                members = [committee_member_from_admin(doc) for doc in approved]
                self._masjid_store.upsert_committee(
                    place_id,
                    {"committee": members},
                )
            if self._listing_store is not None:
                self._listing_store.upsert_listing(
                    place_id,
                    {
                        "admin_status": {
                            "label": "verified",
                            "message": body.message or "Approved",
                        },
                        "message": body.message,
                    },
                )
        elif (
                body.status == AdminRegistrationStatus.REJECTED
                and stored.get("masjid_place_id")
                and self._listing_store is not None
        ):
            self._listing_store.upsert_listing(
                str(stored["masjid_place_id"]),
                {
                    "admin_status": {
                        "label": "unverified",
                        "message": body.message or "Rejected",
                    },
                    "message": body.message,
                },
            )

        self._audit_store.write({
            "action": "admin_status_updated",
            "resource_type": "admin",
            "resource_id": admin_id,
            "user_id": current_user.get("user_id"),
            "details": {"status": body.status.value, "message": body.message},
        })
        log_event(
            "admin",
            "status_updated",
            resource_id=admin_id,
            user_id=current_user.get("user_id"),
            status=body.status.value,
        )
        return self._to_response(stored)

    def _is_onboarding_done(self, doc: Dict[str, Any]) -> bool:
        place_id = doc.get("masjid_place_id")
        if not place_id or self._masjid_store is None:
            return False
        timings = self._masjid_store.get_timings(str(place_id)) or []
        return len(timings) > 0

    def _to_response(self, doc: Dict[str, Any]) -> AdminResponse:
        designation = CommitteeDesignation.normalize(
            doc.get("designation") or (
                doc.get("role")
                if doc.get("role") not in UserRole.values()
                else CommitteeDesignation.ADMIN.value
            ),
        )
        return AdminResponse(
            id=doc["admin_id"],
            name=doc["name"],
            phone=doc["phone"],
            profile_image=doc.get("profile_image"),
            role=doc["role"],
            designation=designation,
            designation_label=CommitteeDesignation.labels().get(designation),
            committee_id=doc.get("committee_id"),
            masjid_place_id=doc.get("masjid_place_id"),
            status=AdminRegistrationStatus(doc["status"]),
            onboarding_done=self._is_onboarding_done(doc),
        )
