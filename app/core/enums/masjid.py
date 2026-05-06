from enum import Enum


class MasjidQueryDefault(int, Enum):
    SEARCH_RADIUS_MIN_M = 500
    SEARCH_RADIUS_MAX_M = 50_000
    NEARBY_RADIUS_M = 1_000
    NEARBY_MAX_RESULTS = 10
    TEXT_SEARCH_MAX_RESULTS = 10
    BY_CITY_MAX_RESULTS = 20
