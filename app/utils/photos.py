from __future__ import annotations

from typing import Any, Dict

_GOOGLE_PLACES_MEDIA_HOST = "https://places.googleapis.com/v1"
_DEFAULT_PHOTO_MAX_HEIGHT_PX = 400


def build_photo_media_url(api_key: str, photo_resource_name: str, max_height_px: int,) -> str:
    base = f"{_GOOGLE_PLACES_MEDIA_HOST}/{photo_resource_name}/media"
    return f"{base}?maxHeightPx={max_height_px}&key={api_key}"


def transform_photos_on_place(place: Dict[str, Any], api_key: str) -> None:
    default_h = _DEFAULT_PHOTO_MAX_HEIGHT_PX
    for photo in place.get("photos") or []:
        if not isinstance(photo, dict) or "name" not in photo:
            continue
        photo_name = photo["name"]
        if not isinstance(photo_name, str) or photo_name.startswith("http"):
            continue
        max_h = photo.get("heightPx") or default_h
        try:
            max_h = int(max_h)
        except (TypeError, ValueError):
            max_h = default_h
        photo["name"] = build_photo_media_url(api_key, photo_name, max_h)


def transform_places_in_search_response(data: Dict[str, Any], api_key: str,) -> Dict[str, Any]:
    for place in data.get("places") or []:
        if isinstance(place, dict):
            transform_photos_on_place(place, api_key)
    return data
