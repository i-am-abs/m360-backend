from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict

from app.core.enums.error_code import ErrorCode
from app.core.enums.role import UserRole
from app.exceptions.base import ApiException
from app.interfaces.audit_log_repository import AuditLogRepository
from app.interfaces.verification_repository import VerificationRepository
from app.schemas.verification import (
    RoleItem,
    RolesResponse,
    VerificationRequestCreate,
    VerificationRequestResponse,
)
from app.utils.structured_log import log_event, log_timing


class VerificationService:
    _ROLE_LABELS = {
        UserRole.ADMIN.value: "Masjid Admin",
        UserRole.SUPER_ADMIN.value: "Super Admin",
    }

    def __init__(
            self,
            verification_store: VerificationRepository,
            audit_store: AuditLogRepository,
    ) -> None:
        self._verification_store = verification_store
        self._audit_store = audit_store

    def list_roles(self) -> RolesResponse:
        roles = [
            RoleItem(id=role_id, label=label)
            for role_id, label in self._ROLE_LABELS.items()
        ]
        return RolesResponse(roles=roles)

    def create_request(
            self,
            body: VerificationRequestCreate,
            current_user: Dict[str, Any],
    ) -> VerificationRequestResponse:
        user_id = current_user.get("user_id")
        if not user_id:
            raise ApiException(
                "Authenticated user required",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.UNAUTHORIZED,
            )

        with log_timing("verification", "create", user_id=user_id):
            stored = self._verification_store.create({
                "user_id": str(user_id),
                "name": body.name,
                "profile_image": body.profile_image,
                "phone": body.phone,
                "role": body.role,
            })

        self._audit_store.write({
            "action": "verification_request_created",
            "resource_type": "verification_request",
            "resource_id": stored["request_id"],
            "user_id": str(user_id),
            "details": {"role": body.role, "phone": body.phone},
        })
        log_event(
            "verification",
            "request_created",
            user_id=user_id,
            resource_id=stored["request_id"],
        )
        return self._to_response(stored)

    def update_status(
            self,
            request_id: str,
            status: str,
            current_user: Dict[str, Any],
    ) -> VerificationRequestResponse:
        from app.core.enums.role import UserRole

        role = current_user.get("role")
        if role != UserRole.SUPER_ADMIN.value:
            raise ApiException(
                "Only super admins can approve verification requests",
                status_code=HTTPStatus.FORBIDDEN.value,
                code=ErrorCode.FORBIDDEN,
            )

        stored = self._verification_store.update_status(
            request_id,
            status,
            updated_by=str(current_user.get("user_id") or ""),
        )
        if not stored:
            raise ApiException(
                "Verification request not found",
                status_code=HTTPStatus.NOT_FOUND.value,
                code=ErrorCode.NOT_FOUND,
            )

        self._audit_store.write({
            "action": "verification_status_updated",
            "resource_type": "verification_request",
            "resource_id": request_id,
            "user_id": current_user.get("user_id"),
            "details": {"status": status},
        })
        log_event(
            "verification",
            "status_updated",
            resource_id=request_id,
            user_id=current_user.get("user_id"),
            status=status,
        )
        return self._to_response(stored)

    @staticmethod
    def _to_response(doc: Dict[str, Any]) -> VerificationRequestResponse:
        return VerificationRequestResponse(
            id=doc["request_id"],
            name=doc["name"],
            profile_image=doc.get("profile_image"),
            phone=doc["phone"],
            role=doc["role"],
            status=doc["status"],
        )
