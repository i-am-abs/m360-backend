from enum import Enum


class SystemConfig(Enum):
    MAX_BYTES = 10 * 1024 * 1024

    REQUEST_TIMEOUT = 10

    MONGO_CONNECTION_TIMEOUT = 5000

    REDIS_CONNECTION_TIMEOUT = 5

    GOOGLE_PLACES_SEARCH_NEARBY_URL = (
        "https://places.googleapis.com/v1/places:searchNearby"
    )
    FIELD_MASK = (
        "places.displayName,places.formattedAddress,places.location,places.photos"
    )
    GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    MSG91_VERIFY_TOKEN_URL = (
        "https://control.msg91.com/api/v5/widget/verifyAccessToken"
    )

    MASJID_SEARCH_FLAG = "masjid_search"
