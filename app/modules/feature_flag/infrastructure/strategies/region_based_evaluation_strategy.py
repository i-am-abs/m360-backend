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


class RegionBasedEvaluationStrategy(FeatureFlagEvaluationStrategyPort):
    supportedConditionType = FeatureFlagConditionType.REGION

    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        if not evaluationContext.regionCode:
            return False

        allowedRegionCodes = self.extractAllowedRegionCodes(
            featureFlagEntity.conditionConfiguration
        )
        if not allowedRegionCodes:
            return False

        normalizedRegionCode = evaluationContext.regionCode.strip().upper()
        return normalizedRegionCode in allowedRegionCodes

    def extractAllowedRegionCodes(self, conditionConfiguration: Dict[str, Any]) -> Set[str]:
        rawRegionCodes = conditionConfiguration.get("allowed_region_codes") or []
        return {str(regionCode).strip().upper() for regionCode in rawRegionCodes}
