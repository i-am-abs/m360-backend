from __future__ import annotations

import zlib
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.domain.entities.masjid_entity import MasjidEntity
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import PlacesReader
from app.interfaces.user_repository import UserRepository
from app.modules.feature_flag.infrastructure.adapters.location_based_feature_flag_adapter import (
    LocationBasedFeatureFlagAdapter,
)

_log = get_logger(__name__)


class UserMasjidService:
    def __init__(
            self,
            userRepository: UserRepository,
            placesReader: PlacesReader,
            locationBasedFeatureFlagService: LocationBasedFeatureFlagAdapter,
            masjidRepository: Optional[MasjidRepository] = None,
    ) -> None:
        self.userRepository = userRepository
        self.placesReader = placesReader
        self.locationBasedFeatureFlagService = locationBasedFeatureFlagService
        self.masjidRepository = masjidRepository

    def listMyMasjids(self, userId: str) -> Dict[str, Any]:
        placeIds = self.userRepository.listFavorites(userId)
        cachedMasjidsByPlaceId = (
            self.masjidRepository.findMasjidsByPlaceIds(placeIds)
            if self.masjidRepository is not None
            else {}
        )

        masjids: List[Dict[str, Any]] = []
        for placeId in placeIds:
            try:
                place = self.resolvePlacePayload(placeId, cachedMasjidsByPlaceId)
                if isinstance(place, dict):
                    self.enrichPlaceWithFeatureFlags(place, placeId)
                masjids.append(place)
            except Exception:
                masjids.append(self.buildUnavailableMasjidPayload(placeId))
        return {"count": len(masjids), "masjids": masjids}

    def addMyMasjid(self, userId: str, placeId: str) -> Dict[str, Any]:
        if self.masjidRepository is not None:
            self.ensureMasjidPersisted(placeId)
        favorites = self.userRepository.addFavorite(userId, placeId)
        return {"place_id": placeId, "favorite_place_ids": favorites}

    def removeMyMasjid(self, userId: str, placeId: str) -> Dict[str, Any]:
        favorites = self.userRepository.removeFavorite(userId, placeId)
        return {"place_id": placeId, "favorite_place_ids": favorites}

    def resolvePlacePayload(
            self,
            placeId: str,
            cachedMasjidsByPlaceId: Dict[str, MasjidEntity],
    ) -> Dict[str, Any]:
        cachedMasjidEntity = cachedMasjidsByPlaceId.get(placeId)
        if cachedMasjidEntity is not None:
            return cachedMasjidEntity.toPlaceDictionary()
        place = self.placesReader.get_place_by_id(placeId)
        if self.masjidRepository is not None and isinstance(place, dict):
            try:
                self.masjidRepository.upsertFromGooglePlacePayload(place)
            except Exception as exc:
                _log.warning("Failed to persist masjid on read place_id=%s (%s)", placeId, exc)
        return place

    def ensureMasjidPersisted(self, placeId: str) -> None:
        if self.masjidRepository is None:
            return
        existingMasjid = self.masjidRepository.findMasjidByPlaceId(placeId)
        if existingMasjid is not None:
            return
        placePayload = self.placesReader.get_place_by_id(placeId)
        if isinstance(placePayload, dict):
            self.masjidRepository.upsertFromGooglePlacePayload(placePayload)

    def enrichPlaceWithFeatureFlags(self, place: Dict[str, Any], placeId: str) -> None:
        location = place.get("location") or {}
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is not None and longitude is not None:
            hasDonations = self.locationBasedFeatureFlagService.isFeatureEnabledAtLocation(
                "DONATIONS_FEATURE", float(latitude), float(longitude)
            )
            hasAnnouncements = self.locationBasedFeatureFlagService.isFeatureEnabledAtLocation(
                "ANNOUNCEMENTS_FEATURE", float(latitude), float(longitude)
            )
        else:
            hasDonations = False
            hasAnnouncements = False

        hashValue = zlib.crc32((placeId or "").encode("utf-8"))
        place["hasDonationsEnabled"] = hasDonations
        place["hasAnnouncementsEnabled"] = hasAnnouncements
        place["donationUpdatesCount"] = (hashValue % 5) if hasDonations else 0
        place["announcementUpdatesCount"] = (hashValue % 7) if hasAnnouncements else 0

    @staticmethod
    def buildUnavailableMasjidPayload(placeId: str) -> Dict[str, Any]:
        return {
            "id": placeId,
            "unavailable": True,
            "hasDonationsEnabled": False,
            "hasAnnouncementsEnabled": False,
            "donationUpdatesCount": 0,
            "announcementUpdatesCount": 0,
        }
