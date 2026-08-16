from __future__ import annotations

from typing import Any, Dict, Optional

import zlib


def normalize_place_id(place_id: Optional[str]) -> str:
    raw = (place_id or "").strip()
    if raw.startswith("places/"):
        raw = raw[len("places/"):]
    return raw


def get_deterministic_masjid_metadata(place_id: str) -> Dict[str, Any]:
    h = zlib.crc32((place_id or "").encode("utf-8"))
    announcement_count = h % 7
    # Donations are opt-in: never enabled by default. Announcements are
    # always enabled for every place_id (including ChIJKwBXQIekdDkRMBaNzvmL3dw).
    return {
        "hasDonationsEnabled": False,
        "hasAnnouncementsEnabled": True,
        "donationUpdatesCount": 0,
        "announcementUpdatesCount": announcement_count,
    }
