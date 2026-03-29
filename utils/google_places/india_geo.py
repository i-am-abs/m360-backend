from typing import Any, Dict

INDIA_RECTANGLE_LOW_LAT = 6.46
INDIA_RECTANGLE_LOW_LNG = 68.11
INDIA_RECTANGLE_HIGH_LAT = 35.51
INDIA_RECTANGLE_HIGH_LNG = 97.40


def india_location_restriction_rectangle() -> Dict[str, Any]:
    return {
        "rectangle": {
            "low": {
                "latitude": INDIA_RECTANGLE_LOW_LAT,
                "longitude": INDIA_RECTANGLE_LOW_LNG,
            },
            "high": {
                "latitude": INDIA_RECTANGLE_HIGH_LAT,
                "longitude": INDIA_RECTANGLE_HIGH_LNG,
            },
        }
    }


def is_point_in_india(latitude: float, longitude: float) -> bool:
    return (
        INDIA_RECTANGLE_LOW_LAT <= latitude <= INDIA_RECTANGLE_HIGH_LAT
        and INDIA_RECTANGLE_LOW_LNG <= longitude <= INDIA_RECTANGLE_HIGH_LNG
    )
