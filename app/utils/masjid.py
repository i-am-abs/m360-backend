from __future__ import annotations

import zlib
from typing import Any, Dict

def get_deterministic_masjid_metadata(place_id: str) -> Dict[str, Any]:
    h = zlib.crc32((place_id or "").encode("utf-8"))
    has_donations = (h % 5) < 3
    has_announcements = (h % 10) < 7
    donation_count = (h % 5) if has_donations else 0
    announcement_count = (h % 7) if has_announcements else 0
    return {
        "hasDonationsEnabled": has_donations,
        "hasAnnouncementsEnabled": has_announcements,
        "donationUpdatesCount": donation_count,
        "announcementUpdatesCount": announcement_count,
    }
