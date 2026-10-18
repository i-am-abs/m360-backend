from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import Settings

_OG_DESC_MAX = 200


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _relative_time(created_at: Any) -> str:
    dt = _parse_dt(created_at)
    if dt is None:
        return ""
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    mins = secs // 60
    if mins < 60:
        return f"{mins} min ago" if mins == 1 else f"{mins} mins ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs} hr ago" if hrs == 1 else f"{hrs} hrs ago"
    days = hrs // 24
    if days < 7:
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} wk ago" if weeks == 1 else f"{weeks} wks ago"
    return dt.strftime("%d %b %Y")


def _minify_places_photo(url: Optional[str], px: int = 96) -> Optional[str]:
    """Request a small Places media variant (avatars render at ~42-49px)."""
    if not url:
        return url
    if "places.googleapis.com" in url:
        if re.search(r"maxHeightPx=\d+", url):
            return re.sub(r"maxHeightPx=\d+", f"maxHeightPx={px}", url)
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}maxHeightPx={px}"
    return url


def _sized_og_image(thumbnail_url: Optional[str], settings: Settings) -> str:
    if thumbnail_url and "image.mux.com" in thumbnail_url:
        sep = "&" if "?" in thumbnail_url else "?"
        return f"{thumbnail_url}{sep}width=1200&height=630&fit_mode=smartcrop"
    if thumbnail_url:
        return thumbnail_url
    return f"{settings.share_web_base_url}/share-static/og-default.png"


def build_share_context(
    message: dict,
    masjid: dict,
    settings: Settings,
    sender_profile: Optional[dict] = None,
    masjid_image_url: Optional[str] = None,
) -> dict:
    message_id = str(message.get("id") or message.get("_id") or "")
    name = (masjid.get("name") or "").strip() or "This masjid"
    location = ", ".join(
        p for p in [masjid.get("city"), masjid.get("state")] if p and str(p).strip()
    ) or (masjid.get("address") or "")
    verified = bool((masjid.get("management") or {}).get("is_claimed"))

    default_masjid_image = (
        f"{settings.share_web_base_url}/share-static/masjid-default.png"
    )
    stored_photos = masjid.get("photos") or []
    if not stored_photos:
        stored_photos = (masjid.get("google_place_data") or {}).get("photos") or []
    first_stored_photo = None
    for photo in stored_photos:
        if isinstance(photo, dict):
            url = photo.get("url") or photo.get("name")
            if url:
                first_stored_photo = str(url)
                break
    masjid_image = _minify_places_photo(
        masjid_image_url
        or first_stored_photo
        or masjid.get("photo_url")
        or default_masjid_image
    )

    text = (message.get("text") or "").strip()
    og_description = (
        (text[: _OG_DESC_MAX - 1] + "…") if len(text) > _OG_DESC_MAX else text
    ) or f"New announcement from {name}"

    msg_type = message.get("message_type") or "text"
    video_url = message.get("video_url") or None
    thumbnail_url = message.get("thumbnail_url") or None
    is_video = msg_type == "video" and bool(video_url)

    sender = message.get("sender") or {}
    profile = sender_profile or {}

    def _clean(value) -> str:
        return str(value or "").strip()

    raw_name = _clean(profile.get("name")) or _clean(sender.get("name"))
    # message.sender.name is often the phone number; never show that as a name.
    if raw_name.isdigit() and len(raw_name) >= 10:
        raw_name = ""
    sender_name = raw_name or "Admin"

    raw_role = _clean(profile.get("role")) or _clean(sender.get("role"))
    if raw_role.lower() in {"admin", "super_admin", "superadmin"}:
        sender_role = "Admin"
    elif raw_role:
        sender_role = raw_role.replace("_", " ").title()
    else:
        sender_role = "Admin"

    sender_avatar = (
        _clean(profile.get("avatar_url"))
        or _clean(sender.get("avatar_url"))
        or masjid_image
    )

    return {
        "message_id": message_id,
        "masjid_name": name,
        "masjid_location": location,
        "masjid_verified": verified,
        "masjid_avatar_url": masjid_image,
        "is_video": is_video,
        "video_hls_url": video_url,
        "poster_url": thumbnail_url,
        "og_image_url": _sized_og_image(thumbnail_url, settings),
        "og_description": og_description,
        "page_title": f"{name} — announcement | Muslim 360",
        "relative_time": _relative_time(message.get("created_at")),
        "canonical_url": f"{settings.share_web_base_url}/s/{message_id}",
        "deep_link_path": f"/s/{message_id}",
        "share_host": settings.share_host,
        "play_store_url": settings.play_store_url,
        "app_store_url": settings.app_store_url,
        "android_package": settings.android_package_name,
        "marketing_site_url": settings.marketing_site_url,
        "sender_name": sender_name,
        "sender_role": sender_role,
        "sender_avatar_url": sender_avatar,
    }
