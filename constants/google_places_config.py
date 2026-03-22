"""Configuration for Google Places (masjid) integration — URLs and field masks."""

from enum import Enum


class GooglePlacesConfig(Enum):
    SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
    SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
    PLACE_DETAILS_BASE = "https://places.googleapis.com/v1/places"

    SEARCH_FIELD_MASK = (
        "places.id,places.name,places.displayName,places.formattedAddress,"
        "places.location,places.photos"
    )
    PLACE_DETAILS_FIELD_MASK = (
        "id,displayName,formattedAddress,location,photos,name"
    )

    PHOTO_MEDIA_DEFAULT_MAX_HEIGHT_PX = 400
