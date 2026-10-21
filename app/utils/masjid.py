from __future__ import annotations

from typing import Any, Dict, Optional

import zlib


def normalize_place_id(place_id: Optional[str]) -> str:
    raw = (place_id or "").strip()
    if raw.startswith("places/"):
        raw = raw[len("places/"):]
    return raw


def is_google_place_id(place_id: Optional[str]) -> bool:
    return normalize_place_id(place_id).startswith("ChIJ")


def is_local_masjid_doc(doc: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(doc, dict):
        return False
    pid = normalize_place_id(str(doc.get("place_id") or doc.get("id") or ""))
    source = str((doc.get("meta") or {}).get("source") or "").lower()
    return pid.startswith("local_") or source in {"manual", "admin"}


def masjid_doc_to_place(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Shape a Mongo masjid document like a Google Places search/details result."""
    pid = normalize_place_id(str(doc.get("place_id") or doc.get("id") or ""))
    lat, lng = _doc_lat_lng(doc)
    contact = doc.get("contact") or {}
    google = doc.get("google_place_data") or {}
    photos = []
    for photo in google.get("photos") or doc.get("photos") or []:
        if not isinstance(photo, dict):
            continue
        url = photo.get("url") or photo.get("name")
        if url:
            photos.append({
                "name": url,
                "width": photo.get("width") or photo.get("widthPx") or 0,
                "height": photo.get("height") or photo.get("heightPx") or 0,
            })
    photo_url = doc.get("photo_url") or (photos[0]["name"] if photos else "")
    place: Dict[str, Any] = {
        "id": pid,
        "name": f"places/{pid}" if pid else "",
        "formattedAddress": doc.get("address") or "",
        "displayName": {"text": doc.get("name") or "", "languageCode": "en"},
        "photos": photos,
        "photo_url": photo_url,
        "internationalPhoneNumber": contact.get("phone") or google.get("phone_number") or "",
        "websiteUri": contact.get("website") or google.get("website") or "",
        "businessStatus": google.get("business_status") or "OPERATIONAL",
    }
    if lat is not None and lng is not None:
        place["location"] = {"latitude": lat, "longitude": lng}
    return place


def _doc_lat_lng(doc: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    loc = doc.get("location") or {}
    if not isinstance(loc, dict):
        return None, None
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        try:
            return float(loc["latitude"]), float(loc["longitude"])
        except (TypeError, ValueError):
            return None, None
    coords = loc.get("coordinates")
    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
        try:
            return float(coords[1]), float(coords[0])
        except (TypeError, ValueError):
            return None, None
    try:
        if loc.get("lat") is not None and loc.get("lng") is not None:
            return float(loc["lat"]), float(loc["lng"])
    except (TypeError, ValueError):
        return None, None
    return None, None


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
