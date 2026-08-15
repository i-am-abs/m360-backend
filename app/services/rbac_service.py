from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Iterable

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.error_code import ErrorCode
from app.core.enums.role import UserRole
from app.exceptions.base import ApiException
from app.interfaces.admin_repository import AdminRepository
from app.utils.admin_link import (
    ensure_admin_user_link,
    is_user_admin_for_place,
)
from app.utils.masjid import normalize_place_id
from app.utils.structured_log import log_event


class RbacService:
    def __init__(self, admin_store: AdminRepository) -> None:
        self._admin_store = admin_store

    def resolve_user_role(self, user: Dict[str, Any]) -> str:
        explicit = user.get("role")
        if explicit == UserRole.SUPER_ADMIN.value:
            return UserRole.SUPER_ADMIN.value

        user_id = user.get("user_id")
        phone = user.get("phone_number")
        admins: list = []
        if user_id:
            admins = ensure_admin_user_link(
                self._admin_store,
                user_id=str(user_id),
                phone=str(phone) if phone else None,
            )
        if not admins and phone:
            admins = self._admin_store.list_by_phone(str(phone), status="approved")

        approved = [
            doc for doc in admins
            if doc.get("status") == AdminRegistrationStatus.APPROVED.value
        ]
        if approved:
            roles = {doc.get("role") for doc in approved}
            if UserRole.SUPER_ADMIN.value in roles:
                return UserRole.SUPER_ADMIN.value
            return UserRole.ADMIN.value

        if explicit in UserRole.values():
            return explicit
        return UserRole.USER.value

    def require_roles(
            self,
            user: Dict[str, Any],
            allowed_roles: Iterable[str],
    ) -> Dict[str, Any]:
        role = self.resolve_user_role(user)
        user_id = user.get("user_id")
        log_event(
            "rbac",
            "role_check",
            user_id=user_id,
            role=role,
            allowed_roles=list(allowed_roles),
        )
        if role not in set(allowed_roles):
            raise ApiException(
                "You do not have permission to perform this action",
                status_code=HTTPStatus.FORBIDDEN.value,
                code=ErrorCode.FORBIDDEN,
            )
        return {**user, "role": role}

    def require_masjid_admin(
            self,
            user: Dict[str, Any],
            place_id: str,
    ) -> Dict[str, Any]:
        target = normalize_place_id(place_id)
        user_id = str(user.get("user_id") or "")
        role = self.resolve_user_role(user)
        log_event(
            "rbac",
            "masjid_access_check",
            user_id=user_id,
            resource_id=target,
            role=role,
        )
        if role == UserRole.SUPER_ADMIN.value:
            return {**user, "role": role}
        if is_user_admin_for_place(
                target,
                current_user=user,
                admin_store=self._admin_store,
        ):
            return {**user, "role": UserRole.ADMIN.value}
        raise ApiException(
            "You are not an admin for this masjid",
            status_code=HTTPStatus.FORBIDDEN.value,
            code=ErrorCode.FORBIDDEN,
        )
