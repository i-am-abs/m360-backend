from enum import Enum


class SystemConfig(Enum):
    MAX_BYTES = 10 * 1024 * 1024

    REQUEST_TIMEOUT = 10

    MONGO_CONNECTION_TIMEOUT = 5e3

    REDIS_CONNECTION_TIMEOUT = 5

    GOOGLE_PLACES_SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
    FIELD_MASK = "places.displayName,places.formattedAddress,places.location"
