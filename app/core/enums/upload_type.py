from __future__ import annotations

from enum import Enum


class UploadMediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
