from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Iterable, Optional

from app.core.enums.error_code import ErrorCode
from app.core.enums.role import UserRole
from app.exceptions.base import ApiException
from app.interfaces.admin_repository import AdminRepository
from app.utils.structured_log import log_event


class RbacService:
    """Role-based access control for masjid admin operations."""

    def __init__(self, admin_store: AdminRepository) -> None:
        self._admin_store = admin_store

    def resolve_user_role(self, user: Dict[str, Any]) -> str:
        explicit = user.get("role")
        if explicit in UserRole.values():
            return explicit

        user_id = user.get("user_id")
        if not user_id:
            return UserRole.USER.value

        admins = self._admin_store.list_by_user_id(str(user_id))
        if not admins:
            return UserRole.USER.value

        roles = {doc.get("role") for doc in admins}
        if UserRole.SUPER_ADMIN.value in roles:
            return UserRole.SUPER_ADMIN.value
        if UserRole.ADMIN.value in roles:
            return UserRole.ADMIN.value
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
        user_with_role = self.require_roles(
            user,
            UserRole.admin_roles() | {UserRole.SUPER_ADMIN.value},
        )
        role = user_with_role["role"]
        if role == UserRole.SUPER_ADMIN.value:
            return user_with_role

        user_id = str(user.get("user_id") or "")
        assignments = self._admin_store.list_by_user_id(user_id)
        place_ids = {
            str(doc.get("masjid_place_id"))
            for doc in assignments
            if doc.get("masjid_place_id")
        }
        log_event(
            "rbac",
            "masjid_access_check",
            user_id=user_id,
            resource_id=place_id,
            assigned_places=list(place_ids),
        )
        if place_id not in place_ids:
            raise ApiException(
                "You are not an admin for this masjid",
                status_code=HTTPStatus.FORBIDDEN.value,
                code=ErrorCode.FORBIDDEN,
            )
        return user_with_role
