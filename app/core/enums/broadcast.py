from __future__ import annotations

from enum import Enum


class BroadcastMessageType(str, Enum):
    VIDEO = "video"
    TEXT = "text"
    ANNOUNCEMENT = "announcement"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


class DevicePlatform(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]
