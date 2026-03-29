from enum import Enum


class GooglePlacesConfig(Enum):
    SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
    SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
    PLACE_DETAILS_BASE = "https://places.googleapis.com/v1/places"

    # Nearby/text search: do not request places.straightLineDistanceMeters here — it is not a
    # root Place field for these methods (invalid field mask → HTTP 400). Distances are
    # computed from location vs search center in the client.
    _PLACES_SEARCH_BASE_FIELDS = (
        "places.id,places.name,places.displayName,places.formattedAddress,"
        "places.location,places.photos"
    )
    SEARCH_TEXT_FIELD_MASK = _PLACES_SEARCH_BASE_FIELDS
    SEARCH_NEARBY_FIELD_MASK = _PLACES_SEARCH_BASE_FIELDS
    PLACE_DETAILS_FIELD_MASK = "id,displayName,formattedAddress,location,photos,name"

    PHOTO_MEDIA_DEFAULT_MAX_HEIGHT_PX = 400
