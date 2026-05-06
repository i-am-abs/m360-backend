from enum import Enum


class GooglePlacesUrl(str, Enum):
    SEARCH_NEARBY = "https://places.googleapis.com/v1/places:searchNearby"
    SEARCH_TEXT = "https://places.googleapis.com/v1/places:searchText"
    PLACE_DETAILS = "https://places.googleapis.com/v1/places"
    MEDIA_HOST = "https://places.googleapis.com/v1"
    GEOCODE = "https://maps.googleapis.com/maps/api/geocode/json"


class GooglePlacesFieldMask(str, Enum):
    SEARCH_NEARBY = (
        "places.id,places.name,places.displayName,places.formattedAddress,"
        "places.location,places.photos"
    )
    SEARCH_TEXT = (
        "places.id,places.name,places.displayName,places.formattedAddress,"
        "places.location,places.photos"
    )
    PLACE_DETAILS = (
        "id,displayName,formattedAddress,location,photos,name,"
        "currentOpeningHours,regularOpeningHours,internationalPhoneNumber,"
        "websiteUri,businessStatus,accessibilityOptions,paymentOptions,"
        "restroom,parkingOptions"
    )


class GooglePlacesPayload(str, Enum):
    PLACE_TYPE_MOSQUE = "mosque"
    RANK_DISTANCE = "DISTANCE"
    REGION_INDIA = "IN"
    GEOCODE_REGION_BIAS = "in"
    GEOCODE_COUNTRY_COMPONENT = "country:IN"


class PhotoConfig(int, Enum):
    DEFAULT_MAX_HEIGHT_PX = 400
