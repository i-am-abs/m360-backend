from __future__ import annotations


class GeographicCoordinate:
    def __init__(self, latitude: float, longitude: float) -> None:
        self.latitude = latitude
        self.longitude = longitude

    def toDictionary(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
        }

    @classmethod
    def fromDictionary(cls, payload: dict) -> GeographicCoordinate:
        return cls(
            latitude=float(payload["latitude"]),
            longitude=float(payload["longitude"]),
        )
