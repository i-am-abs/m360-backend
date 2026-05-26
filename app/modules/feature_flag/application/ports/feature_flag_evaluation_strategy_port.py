from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)


class FeatureFlagEvaluationStrategyPort(ABC):
    supportedConditionType: str

    @abstractmethod
    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        pass
