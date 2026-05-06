"""Geography utilities — haversine distance, India geo-fence."""

from __future__ import annotations

import math

from app.core.enums.geo import EarthConstant, IndiaBounds


def haversine_meters(
        lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
            math.sin(dphi / 2) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EarthConstant.RADIUS_METERS.value * c


def is_point_in_india(latitude: float, longitude: float) -> bool:
    return (
            IndiaBounds.LAT_LOW.value <= latitude <= IndiaBounds.LAT_HIGH.value
            and IndiaBounds.LNG_LOW.value <= longitude <= IndiaBounds.LNG_HIGH.value
    )


def india_location_restriction_rectangle() -> dict:
    return {
        "rectangle": {
            "low": {
                "latitude": IndiaBounds.LAT_LOW.value,
                "longitude": IndiaBounds.LNG_LOW.value,
            },
            "high": {
                "latitude": IndiaBounds.LAT_HIGH.value,
                "longitude": IndiaBounds.LNG_HIGH.value,
            },
        }
    }
