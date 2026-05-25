from __future__ import annotations

from typing import Any, Dict, Set

from app.modules.feature_flag.application.ports.feature_flag_evaluation_strategy_port import (
    FeatureFlagEvaluationStrategyPort,
)
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.enums.feature_flag_condition_type import FeatureFlagConditionType
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)


class EnvironmentBasedEvaluationStrategy(FeatureFlagEvaluationStrategyPort):
    supportedConditionType = FeatureFlagConditionType.ENVIRONMENT

    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        if not evaluationContext.environmentName:
            return False

        allowedEnvironments = self.extractAllowedEnvironments(
            featureFlagEntity.conditionConfiguration
        )
        if not allowedEnvironments:
            return False

        normalizedEnvironmentName = evaluationContext.environmentName.strip().lower()
        return normalizedEnvironmentName in allowedEnvironments

    def extractAllowedEnvironments(self, conditionConfiguration: Dict[str, Any]) -> Set[str]:
        rawEnvironmentNames = conditionConfiguration.get("allowed_environment_names") or []
        return {str(environmentName).strip().lower() for environmentName in rawEnvironmentNames}
