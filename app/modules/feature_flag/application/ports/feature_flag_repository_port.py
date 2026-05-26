from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity


class FeatureFlagRepositoryPort(ABC):
    @abstractmethod
    def saveFeatureFlag(self, featureFlagEntity: FeatureFlagEntity) -> FeatureFlagEntity:
        pass

    @abstractmethod
    def findFeatureFlagByName(self, featureName: str) -> Optional[FeatureFlagEntity]:
        pass

    @abstractmethod
    def findAllFeatureFlags(self) -> List[FeatureFlagEntity]:
        pass

    @abstractmethod
    def deleteFeatureFlagByName(self, featureName: str) -> bool:
        pass

    @abstractmethod
    def countFeatureFlags(self) -> int:
        pass
