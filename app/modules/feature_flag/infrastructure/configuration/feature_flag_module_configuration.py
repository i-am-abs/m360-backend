from __future__ import annotations

from typing import Optional

from pymongo.database import Database

from app.core.config import Settings
from app.modules.feature_flag.application.ports.feature_flag_repository_port import FeatureFlagRepositoryPort
from app.modules.feature_flag.application.services.feature_flag_management_service import (
    FeatureFlagManagementService,
)
from app.modules.feature_flag.infrastructure.adapters.location_based_feature_flag_adapter import (
    LocationBasedFeatureFlagAdapter,
)
from app.modules.feature_flag.infrastructure.factories.feature_flag_evaluation_strategy_factory import (
    FeatureFlagEvaluationStrategyFactory,
)
from app.modules.feature_flag.infrastructure.providers.default_feature_flag_seed_provider import (
    DefaultFeatureFlagSeedProvider,
)
from app.modules.feature_flag.infrastructure.repositories.in_memory_feature_flag_repository import (
    InMemoryFeatureFlagRepository,
)
from app.modules.feature_flag.infrastructure.repositories.mongo_feature_flag_repository import (
    MongoFeatureFlagRepository,
)

class FeatureFlagModuleConfiguration:
    def __init__(self, settings: Settings, mongoDatabase: Optional[Database] = None) -> None:
        self.settings = settings
        self.mongoDatabase = mongoDatabase

    def createFeatureFlagRepository(self) -> FeatureFlagRepositoryPort:
        if self.mongoDatabase is not None:
            return MongoFeatureFlagRepository(self.mongoDatabase)
        return InMemoryFeatureFlagRepository()

    def createEvaluationStrategyFactory(self) -> FeatureFlagEvaluationStrategyFactory:
        return FeatureFlagEvaluationStrategyFactory()

    def createFeatureFlagManagementService(
            self,
            featureFlagRepository: Optional[FeatureFlagRepositoryPort] = None,
    ) -> FeatureFlagManagementService:
        repository = featureFlagRepository or self.createFeatureFlagRepository()
        seedProvider = DefaultFeatureFlagSeedProvider()
        seedProvider.seedFeatureFlagsIfEmpty(repository)

        managementService = FeatureFlagManagementService(
            featureFlagRepository=repository,
            evaluationStrategyFactory=self.createEvaluationStrategyFactory(),
            runtimeEnvironmentName=self.settings.app_env,
        )
        managementService.refreshFeatureFlagCache()
        return managementService

    def createLocationBasedFeatureFlagAdapter(
            self,
            featureFlagManagementService: Optional[FeatureFlagManagementService] = None,
    ) -> LocationBasedFeatureFlagAdapter:
        managementService = featureFlagManagementService or self.createFeatureFlagManagementService()
        return LocationBasedFeatureFlagAdapter(managementService)
