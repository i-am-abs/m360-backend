from __future__ import annotations

from enum import Enum


class PlatformFeature(str, Enum):
    VERIFICATION = "verification"
    TIMINGS = "timings"
    COMMITTEE_REGISTRATION = "committee_registration"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def default_flags(cls) -> dict[str, bool]:
        return {member.value: False for member in cls}
