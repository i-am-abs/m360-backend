from __future__ import annotations

from typing import Any, Dict, Set

from app.modules.feature_flag.application.ports.feature_flag_evaluation_strategy_port import (
    FeatureFlagEvaluationStrategyPort,
)
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)


class UserBasedEvaluationStrategy(FeatureFlagEvaluationStrategyPort):
    supportedConditionType = "USER"

    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        if not evaluationContext.userId:
            return False

        allowedUserIds = self.extractAllowedUserIds(featureFlagEntity.conditionConfiguration)
        blockedUserIds = self.extractBlockedUserIds(featureFlagEntity.conditionConfiguration)

        if evaluationContext.userId in blockedUserIds:
            return False
        if not allowedUserIds:
            return False
        return evaluationContext.userId in allowedUserIds

    def extractAllowedUserIds(self, conditionConfiguration: Dict[str, Any]) -> Set[str]:
        rawUserIds = conditionConfiguration.get("allowed_user_ids") or []
        return {str(userId) for userId in rawUserIds}

    def extractBlockedUserIds(self, conditionConfiguration: Dict[str, Any]) -> Set[str]:
        rawUserIds = conditionConfiguration.get("blocked_user_ids") or []
        return {str(userId) for userId in rawUserIds}
