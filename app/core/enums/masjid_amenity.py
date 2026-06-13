from __future__ import annotations

from enum import Enum


class Amenity(str, Enum):
    """Supported masjid amenities.

    Each value is the stable string identifier stored in MongoDB and
    returned in the API response.  The client is responsible for mapping
    these keys to display labels and icons.
    """

    CAR_PARKING = "car_parking"
    BIKE_PARKING = "bike_parking"
    LANGAR_FOOD = "langar_food"
    WAZU_AREA = "wazu_area"            # Wudhu / ablution area
    IMAM_AVAILABLE = "imam_available"
    LIFT = "lift"                       # Elevator
    DRINKING_WATER = "drinking_water"
    WHEELCHAIR_ACCESS = "wheelchair_access"
    ISLAMIC_LIBRARY = "islamic_library"
    SEATING_AREA = "seating_area"
    BOOK_SHELF = "book_shelf"
    AC = "ac"
    AIR_COOLERS = "air_coolers"
    MAKTAB = "maktab"

    @classmethod
    def values(cls) -> list[str]:
        """Return a list of all valid amenity string values."""
        return [member.value for member in cls]
