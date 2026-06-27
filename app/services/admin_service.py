from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Optional

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.error_code import ErrorCode
from app.core.enums.role import UserRole
from app.exceptions.base import ApiException
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.audit_log_repository import AuditLogRepository
from app.schemas.admin import AdminRegisterRequest, AdminResponse, AdminStatusUpdateRequest
from app.services.rbac_service import RbacService
from app.utils.structured_log import log_event, log_timing


class AdminService:
    def __init__(
            self,
            admin_store: AdminRepository,
            audit_store: AuditLogRepository,
            rbac: RbacService,
    ) -> None:
        self._admin_store = admin_store
        self._audit_store = audit_store
        self._rbac = rbac

    def register(
            self,
            request: AdminRegisterRequest,
            *,
            current_user: Optional[Dict[str, Any]] = None,
    ) -> AdminResponse:
        with log_timing("admin", "register", phone=request.phone):
            if request.role == UserRole.SUPER_ADMIN:
                if not current_user:
                    raise ApiException(
                        "Super admin registration requires authentication",
                        status_code=HTTPStatus.FORBIDDEN.value,
                        code=ErrorCode.FORBIDDEN,
                    )
                self._rbac.require_roles(current_user, {UserRole.SUPER_ADMIN.value})

            try:
                stored = self._admin_store.create({
                    "user_id": current_user.get("user_id") if current_user else None,
                    "name": request.name,
                    "phone": request.phone,
                    "profile_image": request.profile_image,
                    "role": request.role.value,
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
            "user_id": current_user.get("user_id") if current_user else None,
            "details": {"phone": request.phone, "role": request.role.value},
        })
        log_event(
            "admin",
            "registered",
            resource_id=stored["admin_id"],
            user_id=current_user.get("user_id") if current_user else None,
        )
        return self._to_response(stored)

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

    @staticmethod
    def _to_response(doc: Dict[str, Any]) -> AdminResponse:
        return AdminResponse(
            id=doc["admin_id"],
            name=doc["name"],
            phone=doc["phone"],
            profile_image=doc.get("profile_image"),
            role=doc["role"],
            committee_id=doc.get("committee_id"),
            masjid_place_id=doc.get("masjid_place_id"),
            status=AdminRegistrationStatus(doc["status"]),
        )
