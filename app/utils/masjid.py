from __future__ import annotations

from typing import Any, Dict

import zlib


def get_deterministic_masjid_metadata(place_id: str) -> Dict[str, Any]:
    h = zlib.crc32((place_id or "").encode("utf-8"))
    has_donations = (h % 5) < 3
    donation_count = (h % 5) if has_donations else 0
    announcement_count = h % 7
    # Always enabled for every place_id (including ChIJKwBXQIekdDkRMBaNzvmL3dw).
    return {
        "hasDonationsEnabled": has_donations,
        "hasAnnouncementsEnabled": True,
        "donationUpdatesCount": donation_count,
        "announcementUpdatesCount": announcement_count,
    }
