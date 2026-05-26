from __future__ import annotations

from typing import Optional

from pymongo import MongoClient
from redis import Redis

from app.core.config import Settings
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.modules.feature_flag.infrastructure.adapters.location_based_feature_flag_adapter import (
    LocationBasedFeatureFlagAdapter,
)
from app.modules.masjid.facade.masjid_module_facade import MasjidModuleFacade
from app.repositories.google_places_client import GooglePlacesClient
from app.repositories.mongo_masjid_store import MongoMasjidStore
from app.services.cached_masjid_search_service import CachedMasjidSearchService
from app.services.masjid_search_service import GoogleMasjidSearchService
from app.services.persisting_masjid_search_service import PersistingMasjidSearchService
from app.services.user_masjid_service import UserMasjidService


class MasjidModuleConfiguration:
    def __init__(
            self,
            settings: Settings,
            redisClient: Optional[Redis],
            mongoClient: Optional[MongoClient],
            userRepository: UserRepository,
            locationBasedFeatureFlagAdapter: LocationBasedFeatureFlagAdapter,
            redisCacheModuleActive: bool,
    ) -> None:
        self.settings = settings
        self.redisClient = redisClient
        self.mongoClient = mongoClient
        self.userRepository = userRepository
        self.locationBasedFeatureFlagAdapter = locationBasedFeatureFlagAdapter
        self.redisCacheModuleActive = redisCacheModuleActive

    def createFacade(self) -> MasjidModuleFacade:
        masjidRepository = self._createMasjidRepository()
        masjidSearchService = self._createMasjidSearchService(masjidRepository)

        return MasjidModuleFacade(
            masjidSearchService=masjidSearchService,
            userMasjidService=UserMasjidService(
                userRepository=self.userRepository,
                placesReader=masjidSearchService,
                locationBasedFeatureFlagService=self.locationBasedFeatureFlagAdapter,
                masjidRepository=masjidRepository,
            ),
            masjidRepository=masjidRepository,
        )

    def _createMasjidRepository(self) -> Optional[MasjidRepository]:
        if self.mongoClient is None:
            return None
        mongoDatabase = self.mongoClient.get_database(self.settings.mongodb_database)
        return MongoMasjidStore(mongoDatabase)

    def _createMasjidSearchService(
            self,
            masjidRepository: Optional[MasjidRepository],
    ) -> MasjidSearchService:
        placesClient = GooglePlacesClient(
            api_key=self.settings.google_places_api_key or "",
            timeout=self.settings.request_timeout_seconds,
        )
        innerMasjidSearchService: MasjidSearchService = GoogleMasjidSearchService(placesClient)

        if (
                self.redisCacheModuleActive
                and self.redisClient is not None
                and self.settings.api_get_cache_ttl_seconds > 0
        ):
            innerMasjidSearchService = CachedMasjidSearchService(
                innerMasjidSearchService,
                self.redisClient,
                self.settings.api_get_cache_ttl_seconds,
                self.settings.redis_key_prefix,
            )

        if masjidRepository is not None:
            return PersistingMasjidSearchService(
                innerMasjidSearchService=innerMasjidSearchService,
                masjidRepository=masjidRepository,
                masjidCacheTtlSeconds=self.settings.masjid_cache_ttl_seconds,
            )
        return innerMasjidSearchService
