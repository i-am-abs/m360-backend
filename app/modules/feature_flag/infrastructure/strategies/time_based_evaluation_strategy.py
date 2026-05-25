from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.modules.feature_flag.application.ports.feature_flag_evaluation_strategy_port import (
    FeatureFlagEvaluationStrategyPort,
)
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.enums.feature_flag_condition_type import FeatureFlagConditionType
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)


class TimeBasedEvaluationStrategy(FeatureFlagEvaluationStrategyPort):
    supportedConditionType = FeatureFlagConditionType.TIME_BASED

    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        activeFromTimestamp = self.parseTimestamp(
            featureFlagEntity.conditionConfiguration.get("active_from_timestamp")
        )
        activeUntilTimestamp = self.parseTimestamp(
            featureFlagEntity.conditionConfiguration.get("active_until_timestamp")
        )
        evaluationTimestamp = evaluationContext.evaluationTimestamp

        if activeFromTimestamp is not None and evaluationTimestamp < activeFromTimestamp:
            return False
        if activeUntilTimestamp is not None and evaluationTimestamp > activeUntilTimestamp:
            return False
        return activeFromTimestamp is not None or activeUntilTimestamp is not None

    def parseTimestamp(self, rawTimestamp: Any) -> Optional[datetime]:
        if rawTimestamp is None:
            return None
        if isinstance(rawTimestamp, datetime):
            if rawTimestamp.tzinfo is None:
                return rawTimestamp.replace(tzinfo=timezone.utc)
            return rawTimestamp
        try:
            parsedTimestamp = datetime.fromisoformat(str(rawTimestamp))
        except ValueError:
            return None
        if parsedTimestamp.tzinfo is None:
            return parsedTimestamp.replace(tzinfo=timezone.utc)
        return parsedTimestamp
