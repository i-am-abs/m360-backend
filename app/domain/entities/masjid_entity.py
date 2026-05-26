from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


class MasjidEntity:
    def __init__(self, placeId: str, googlePlacePayload: Dict[str, Any], createdAt: Optional[datetime] = None, updatedAt: Optional[datetime] = None, lastFetchedAt: Optional[datetime] = None) -> None:
        self.placeId = placeId
        self.googlePlacePayload = googlePlacePayload
        self.createdAt = createdAt or datetime.now(timezone.utc)
        self.updatedAt = updatedAt or self.createdAt
        self.lastFetchedAt = lastFetchedAt or self.updatedAt

    def extractDisplayName(self) -> Optional[str]:
        displayName = self.googlePlacePayload.get("displayName") or {}
        if isinstance(displayName, dict):
            return displayName.get("text")
        return None

    def extractFormattedAddress(self) -> Optional[str]:
        return self.googlePlacePayload.get("formattedAddress")

    def extractLatitude(self) -> Optional[float]:
        location = self.googlePlacePayload.get("location") or {}
        latitude = location.get("latitude")
        if latitude is None:
            return None
        return float(latitude)

    def extractLongitude(self) -> Optional[float]:
        location = self.googlePlacePayload.get("location") or {}
        longitude = location.get("longitude")
        if longitude is None:
            return None
        return float(longitude)

    def toPlaceDictionary(self) -> Dict[str, Any]:
        return dict(self.googlePlacePayload)

    def toDictionary(self) -> Dict[str, Any]:
        return {
            "place_id": self.placeId,
            "google_place_payload": self.googlePlacePayload,
            "display_name": self.extractDisplayName(),
            "formatted_address": self.extractFormattedAddress(),
            "latitude": self.extractLatitude(),
            "longitude": self.extractLongitude(),
            "created_at": self.createdAt.isoformat(),
            "updated_at": self.updatedAt.isoformat(),
            "last_fetched_at": self.lastFetchedAt.isoformat(),
        }

    @classmethod
    def fromDictionary(cls, payload: Dict[str, Any]) -> MasjidEntity:
        return cls(
            placeId=str(payload["place_id"]),
            googlePlacePayload=dict(payload.get("google_place_payload") or {}),
            createdAt=datetime.fromisoformat(str(payload["created_at"])),
            updatedAt=datetime.fromisoformat(str(payload["updated_at"])),
            lastFetchedAt=datetime.fromisoformat(str(payload["last_fetched_at"])),
        )

    @classmethod
    def fromGooglePlacePayload(cls, googlePlacePayload: Dict[str, Any]) -> MasjidEntity:
        placeId = str(googlePlacePayload.get("id") or "").strip()
        if not placeId:
            raise ValueError("Google place payload must include a non-empty id.")
        now = datetime.now(timezone.utc)
        return cls(
            placeId=placeId,
            googlePlacePayload=googlePlacePayload,
            createdAt=now,
            updatedAt=now,
            lastFetchedAt=now,
        )
