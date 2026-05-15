from enum import Enum


class IndiaBounds(float, Enum):
    LAT_LOW = 6.46
    LAT_HIGH = 35.51
    LNG_LOW = 68.11
    LNG_HIGH = 97.40


class EarthConstant(float, Enum):
    RADIUS_METERS = 6_371_000.0
