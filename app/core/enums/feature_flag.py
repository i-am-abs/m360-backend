from __future__ import annotations

from enum import Enum
from typing import Optional


class MatchSource(str, Enum):
    LOCATION_KEY = "location_key"
    COORDINATES = "coordinates"
    REGION = "region"
    DEFAULT = "default"
    NONE = "none"


class PlatformFeature(str, Enum):
    VERIFICATION = "verification"
    TIMINGS = "timings"
    COMMITTEE_REGISTRATION = "committee_registration"
    MASJID_DISCOVERY = "masjid_discovery"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def default_flags(cls) -> dict[str, bool]:
        return {member.value: False for member in cls}

    @classmethod
    def launch_gated(cls) -> set["PlatformFeature"]:
        return {cls.MASJID_DISCOVERY}

    @classmethod
    def parse(cls, value: Optional[str]) -> Optional["PlatformFeature"]:
        if value is None:
            return None
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if not key:
            return None
        for member in cls:
            if member.value == key:
                return member
        return _MODULE_ALIASES.get(key)

    def is_launch_gated(self) -> bool:
        return self in self.launch_gated()


_MODULE_ALIASES: dict[str, PlatformFeature] = {
    "masjid": PlatformFeature.MASJID_DISCOVERY,
    "masjids": PlatformFeature.MASJID_DISCOVERY,
    "masjid_module": PlatformFeature.MASJID_DISCOVERY,
    "masjid_tab": PlatformFeature.MASJID_DISCOVERY,
    "discovery": PlatformFeature.MASJID_DISCOVERY,
    "committee": PlatformFeature.COMMITTEE_REGISTRATION,
    "committee_registrations": PlatformFeature.COMMITTEE_REGISTRATION,
    "timing": PlatformFeature.TIMINGS,
    "prayer_timings": PlatformFeature.TIMINGS,
    "verify": PlatformFeature.VERIFICATION,
}


def module_names() -> list[str]:
    return sorted(set(PlatformFeature.values()) | set(_MODULE_ALIASES))
