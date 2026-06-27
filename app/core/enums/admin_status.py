from __future__ import annotations

from enum import Enum


class AdminRegistrationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]
