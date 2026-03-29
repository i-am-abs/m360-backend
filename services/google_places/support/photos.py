from typing import Any, Dict

from constants.google_places_config import GooglePlacesConfig


def build_photo_media_url(
    api_key: str,
    photo_resource_name: str,
    max_height_px: int,
) -> str:
    base = f"{GooglePlacesConfig.PLACES_MEDIA_HOST.value}/{photo_resource_name}/media"
    return f"{base}?maxHeightPx={max_height_px}&key={api_key}"


def transform_photos_on_place(place: Dict[str, Any], api_key: str) -> None:
    default_h = GooglePlacesConfig.PHOTO_MEDIA_DEFAULT_MAX_HEIGHT_PX.value
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


def transform_places_in_search_response(
    data: Dict[str, Any],
    api_key: str,
) -> Dict[str, Any]:
    for place in data.get("places") or []:
        if isinstance(place, dict):
            transform_photos_on_place(place, api_key)
    return data
