from __future__ import annotations

import hashlib
from typing import Any, Dict

from app.modules.feature_flag.application.ports.feature_flag_evaluation_strategy_port import (
    FeatureFlagEvaluationStrategyPort,
)
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.enums.feature_flag_condition_type import FeatureFlagConditionType
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)


class PercentageRolloutEvaluationStrategy(FeatureFlagEvaluationStrategyPort):
    supportedConditionType = FeatureFlagConditionType.PERCENTAGE_ROLLOUT

    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        rolloutPercentage = self.extractRolloutPercentage(featureFlagEntity.conditionConfiguration)
        if rolloutPercentage <= 0:
            return False
        if rolloutPercentage >= 100:
            return True

        rolloutKey = self.buildRolloutKey(featureFlagEntity, evaluationContext)
        bucketValue = self.computeStableBucketValue(rolloutKey)
        return bucketValue < rolloutPercentage

    def extractRolloutPercentage(self, conditionConfiguration: Dict[str, Any]) -> float:
        rawPercentage = conditionConfiguration.get("rollout_percentage", 0)
        try:
            rolloutPercentage = float(rawPercentage)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(100.0, rolloutPercentage))

    def buildRolloutKey(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> str:
        rolloutSalt = str(
            featureFlagEntity.conditionConfiguration.get("rollout_salt") or featureFlagEntity.featureName
        )
        userIdentifier = evaluationContext.userId or "anonymous"
        return f"{featureFlagEntity.featureName}:{rolloutSalt}:{userIdentifier}"

    def computeStableBucketValue(self, rolloutKey: str) -> float:
        digest = hashlib.sha256(rolloutKey.encode("utf-8")).hexdigest()
        bucketInteger = int(digest[:8], 16)
        return (bucketInteger / 0xFFFFFFFF) * 100.0
