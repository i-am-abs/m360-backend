from __future__ import annotations

from enum import Enum


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"

    @classmethod
    def choices(cls):
        return [(member.value, member.name.replace("_", " ").title()) for member in cls]
