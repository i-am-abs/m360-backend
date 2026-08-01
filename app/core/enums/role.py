from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def admin_roles(cls) -> set[str]:
        return {cls.SUPER_ADMIN.value, cls.ADMIN.value}
