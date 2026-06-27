from __future__ import annotations

from enum import Enum


class PrayerName(str, Enum):
    FAJR = "fajr"
    DHUHR = "dhuhr"
    ASR = "asr"
    MAGHRIB = "maghrib"
    ISHA = "isha"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]
