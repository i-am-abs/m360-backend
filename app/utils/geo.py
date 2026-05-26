from __future__ import annotations

import math

INDIA_LAT_LOW = 6.46
INDIA_LAT_HIGH = 35.51
INDIA_LNG_LOW = 68.11
INDIA_LNG_HIGH = 97.40
EARTH_RADIUS_METERS = 6_371_000.0


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float,) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
            math.sin(dphi / 2) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_METERS * c


def is_point_in_india(latitude: float, longitude: float) -> bool:
    return (
            INDIA_LAT_LOW <= latitude <= INDIA_LAT_HIGH
            and INDIA_LNG_LOW <= longitude <= INDIA_LNG_HIGH
    )


def india_location_restriction_rectangle() -> dict:
    return {
        "rectangle": {
            "low": {
                "latitude": INDIA_LAT_LOW,
                "longitude": INDIA_LNG_LOW,
            },
            "high": {
                "latitude": INDIA_LAT_HIGH,
                "longitude": INDIA_LNG_HIGH,
            },
        }
    }
