from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional

from app.modules.feature_flag.application.ports.feature_flag_repository_port import FeatureFlagRepositoryPort
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity


class InMemoryFeatureFlagRepository(FeatureFlagRepositoryPort):
    def __init__(self) -> None:
        self.featureFlagStorageByName: Dict[str, FeatureFlagEntity] = {}
        self.repositoryLock = RLock()

    def saveFeatureFlag(self, featureFlagEntity: FeatureFlagEntity) -> FeatureFlagEntity:
        with self.repositoryLock:
            self.featureFlagStorageByName[featureFlagEntity.featureName] = featureFlagEntity
            return featureFlagEntity

    def findFeatureFlagByName(self, featureName: str) -> Optional[FeatureFlagEntity]:
        with self.repositoryLock:
            return self.featureFlagStorageByName.get(featureName.strip().upper())

    def findAllFeatureFlags(self) -> List[FeatureFlagEntity]:
        with self.repositoryLock:
            return sorted(
                self.featureFlagStorageByName.values(),
                key=lambda featureFlagEntity: featureFlagEntity.featureName,
            )

    def deleteFeatureFlagByName(self, featureName: str) -> bool:
        with self.repositoryLock:
            normalizedFeatureName = featureName.strip().upper()
            if normalizedFeatureName not in self.featureFlagStorageByName:
                return False
            del self.featureFlagStorageByName[normalizedFeatureName]
            return True

    def countFeatureFlags(self) -> int:
        with self.repositoryLock:
            return len(self.featureFlagStorageByName)
