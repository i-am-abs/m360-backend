from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.domain.entities.masjid_entity import MasjidEntity
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService

_log = get_logger(__name__)


class PersistingMasjidSearchService(MasjidSearchService):
    def __init__(
            self,
            innerMasjidSearchService: MasjidSearchService,
            masjidRepository: MasjidRepository,
            masjidCacheTtlSeconds: int,
    ) -> None:
        self.innerMasjidSearchService = innerMasjidSearchService
        self.masjidRepository = masjidRepository
        self.masjidCacheTtlSeconds = masjidCacheTtlSeconds

    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        cachedMasjidEntity = self.masjidRepository.findMasjidByPlaceId(place_id)
        if cachedMasjidEntity is not None and not self.isMasjidCacheStale(cachedMasjidEntity):
            return cachedMasjidEntity.toPlaceDictionary()

        googlePlacePayload = self.innerMasjidSearchService.get_place_by_id(place_id)
        self.persistGooglePlacePayload(googlePlacePayload)
        return googlePlacePayload

    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
    ) -> Dict[str, Any]:
        searchResponse = self.innerMasjidSearchService.search_nearby(
            latitude,
            longitude,
            radius_meters,
            max_result_count,
        )
        self.persistPlacesFromSearchResponse(searchResponse)
        return searchResponse

    def search_by_name(
            self,
            query: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        searchResponse = self.innerMasjidSearchService.search_by_name(
            query,
            max_result_count,
            radius_meters,
        )
        self.persistPlacesFromSearchResponse(searchResponse)
        return searchResponse

    def search_by_city(
            self,
            city: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        searchResponse = self.innerMasjidSearchService.search_by_city(
            city,
            max_result_count,
            radius_meters,
        )
        self.persistPlacesFromSearchResponse(searchResponse)
        return searchResponse

    def isMasjidCacheStale(self, masjidEntity: MasjidEntity) -> bool:
        if self.masjidCacheTtlSeconds <= 0:
            return False
        cacheAgeSeconds = (datetime.now(timezone.utc) - masjidEntity.lastFetchedAt).total_seconds()
        return cacheAgeSeconds > self.masjidCacheTtlSeconds

    def persistPlacesFromSearchResponse(self, searchResponse: Dict[str, Any]) -> None:
        for placePayload in searchResponse.get("places") or []:
            if isinstance(placePayload, dict):
                self.persistGooglePlacePayload(placePayload)

    def persistGooglePlacePayload(self, googlePlacePayload: Dict[str, Any]) -> None:
        if not isinstance(googlePlacePayload, dict):
            return
        placeId = str(googlePlacePayload.get("id") or "").strip()
        if not placeId:
            return
        try:
            self.masjidRepository.upsertFromGooglePlacePayload(googlePlacePayload)
        except Exception as exc:
            _log.warning("Failed to persist masjid place_id=%s (%s)", placeId, exc)

    def findCachedPlaceById(self, placeId: str) -> Optional[Dict[str, Any]]:
        masjidEntity = self.masjidRepository.findMasjidByPlaceId(placeId)
        if masjidEntity is None:
            return None
        return masjidEntity.toPlaceDictionary()
