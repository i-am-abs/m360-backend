from enum import Enum

_PLACES_SEARCH_BASE_FIELDS = (
    "places.id,places.name,places.displayName,places.formattedAddress,"
    "places.location,places.photos"
)


class GooglePlacesConfig(Enum):
    SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
    SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
    PLACE_DETAILS_BASE = "https://places.googleapis.com/v1/places"
    GEOCODE_JSON_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    PLACES_MEDIA_HOST = "https://places.googleapis.com/v1"

    SEARCH_TEXT_FIELD_MASK = _PLACES_SEARCH_BASE_FIELDS
    SEARCH_NEARBY_FIELD_MASK = _PLACES_SEARCH_BASE_FIELDS
    PLACE_DETAILS_FIELD_MASK = (
        "id,displayName,formattedAddress,location,photos,name,"
        "currentOpeningHours,regularOpeningHours,internationalPhoneNumber,"
        "websiteUri,businessStatus,accessibilityOptions,paymentOptions,"
        "restroom,parkingOptions"
    )

    PHOTO_MEDIA_DEFAULT_MAX_HEIGHT_PX = 400


class GooglePlacesPayload:
    PLACE_TYPE_MOSQUE = "mosque"
    RANK_PREFERENCE_DISTANCE = "DISTANCE"
    REGION_CODE_INDIA = "IN"
    GEOCODE_REGION_BIAS = "in"
    GEOCODE_COUNTRY_COMPONENTS = "country:IN"
