from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AmenityKey(str, Enum):
    CAR_PARKING = "car_parking"
    WUZU = "wuzu"
    AIR_COOLERS = "air_coolers"
    IFTAR = "iftar"
    CAPACITY = "capacity"
    MAKTAB = "maktab"
    MALE_WASHROOM = "male_washroom"
    DRINKING_WATER = "drinking_water"
    WHEELCHAIR_ACCESSIBILITY = "wheelchair_accessibility"
    MUSHAF = "mushaf"
    CHAIRS_FOR_ELDERLY = "chairs_for_elderly"
    JANAZAH_FACILITIES = "janazah_facilities"


AMENITIES_MASTER = [
    {"key": "car_parking", "label": "Car Parking", "icon": "local_parking"},
    {"key": "wuzu", "label": "Wuzu", "icon": "water_drop"},
    {"key": "air_coolers", "label": "Air Coolers", "icon": "ac_unit"},
    {"key": "iftar", "label": "Iftar", "icon": "restaurant"},
    {"key": "capacity", "label": "Capacity", "icon": "groups"},
    {"key": "maktab", "label": "Maktab", "icon": "school"},
    {"key": "male_washroom", "label": "Male Washroom", "icon": "wc"},
    {"key": "drinking_water", "label": "Drinking Water", "icon": "local_drink"},
    {
        "key": "wheelchair_accessibility",
        "label": "Wheelchair Accessibility",
        "icon": "accessible",
    },
    {"key": "mushaf", "label": "Mushaf", "icon": "menu_book"},
    {"key": "chairs_for_elderly", "label": "Chairs for Elderly", "icon": "chair"},
    {"key": "janazah_facilities", "label": "Janazah Facilities", "icon": "mosque"},
]

VALID_AMENITY_KEYS = {a["key"] for a in AMENITIES_MASTER}


class AmenityToggleRequest(BaseModel):
    amenity_key: AmenityKey
    action: str = Field(..., pattern="^(add|remove)$")


class BulkAmenityRequest(BaseModel):
    amenities: List[AmenityKey]


class MasjidCreateRequest(BaseModel):
    masjid_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: List[AmenityKey] = Field(default_factory=list)
