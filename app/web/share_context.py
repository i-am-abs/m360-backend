from __future__ import annotations

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


def _sized_og_image(thumbnail_url: Optional[str], settings: Settings) -> str:
    if thumbnail_url and "image.mux.com" in thumbnail_url:
        sep = "&" if "?" in thumbnail_url else "?"
        return f"{thumbnail_url}{sep}width=1200&height=630&fit_mode=smartcrop"
    if thumbnail_url:
        return thumbnail_url
    return f"{settings.share_web_base_url}/share-static/og-default.png"


def build_share_context(
    message: dict, masjid: dict, settings: Settings
) -> dict:
    message_id = str(message.get("id") or message.get("_id") or "")
    name = (masjid.get("name") or "").strip() or "This masjid"
    location = ", ".join(
        p for p in [masjid.get("city"), masjid.get("state")] if p and str(p).strip()
    ) or (masjid.get("address") or "")
    verified = bool((masjid.get("management") or {}).get("is_claimed"))

    text = (message.get("text") or "").strip()
    og_description = (
        (text[: _OG_DESC_MAX - 1] + "…") if len(text) > _OG_DESC_MAX else text
    ) or f"New announcement from {name}"

    msg_type = message.get("message_type") or "text"
    video_url = message.get("video_url") or None
    thumbnail_url = message.get("thumbnail_url") or None
    is_video = msg_type == "video" and bool(video_url)

    return {
        "message_id": message_id,
        "masjid_name": name,
        "masjid_location": location,
        "masjid_verified": verified,
        "masjid_avatar_url": masjid.get("photo_url")
        or f"{settings.share_web_base_url}/share-static/masjid-default.png",
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
    }
