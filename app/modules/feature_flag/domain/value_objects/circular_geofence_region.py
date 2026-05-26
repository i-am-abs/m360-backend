from __future__ import annotations

import math

from app.modules.feature_flag.domain.value_objects.geographic_coordinate import GeographicCoordinate


class CircularGeofenceRegion:
    EARTH_RADIUS_IN_METERS: float = 6371000.0

    def __init__(
            self,
            centerCoordinate: GeographicCoordinate,
            radiusInMeters: float,
    ) -> None:
        self.centerCoordinate = centerCoordinate
        self.radiusInMeters = radiusInMeters

    def containsCoordinate(self, targetCoordinate: GeographicCoordinate) -> bool:
        lat1Rad = math.radians(self.centerCoordinate.latitude)
        lon1Rad = math.radians(self.centerCoordinate.longitude)
        lat2Rad = math.radians(targetCoordinate.latitude)
        lon2Rad = math.radians(targetCoordinate.longitude)

        deltaLatRad = lat2Rad - lat1Rad
        deltaLonRad = lon2Rad - lon1Rad

        haversineIntermediateValue = (
            math.sin(deltaLatRad / 2.0) ** 2
            + math.cos(lat1Rad) * math.cos(lat2Rad) * math.sin(deltaLonRad / 2.0) ** 2
        )
        centralAngleRadians = 2.0 * math.atan2(
            math.sqrt(haversineIntermediateValue),
            math.sqrt(max(0.0, 1.0 - haversineIntermediateValue)),
        )
        distanceInMeters = self.EARTH_RADIUS_IN_METERS * centralAngleRadians
        return distanceInMeters <= self.radiusInMeters

    def toDictionary(self) -> dict:
        return {
            "center_latitude": self.centerCoordinate.latitude,
            "center_longitude": self.centerCoordinate.longitude,
            "radius_in_meters": self.radiusInMeters,
        }

    @classmethod
    def fromDictionary(cls, payload: dict) -> CircularGeofenceRegion:
        centerCoordinate = GeographicCoordinate(
            latitude=float(payload["center_latitude"]),
            longitude=float(payload["center_longitude"]),
        )
        return cls(
            centerCoordinate=centerCoordinate,
            radiusInMeters=float(payload["radius_in_meters"]),
        )
