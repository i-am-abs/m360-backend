from __future__ import annotations

from typing import Any, Dict, List

from app.modules.feature_flag.application.ports.feature_flag_evaluation_strategy_port import (
    FeatureFlagEvaluationStrategyPort,
)
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.enums.feature_flag_condition_type import FeatureFlagConditionType
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.feature_flag.infrastructure.factories.feature_flag_evaluation_strategy_factory import (
        FeatureFlagEvaluationStrategyFactory,
    )


class CompositeEvaluationStrategy(FeatureFlagEvaluationStrategyPort):
    supportedConditionType = FeatureFlagConditionType.COMPOSITE

    def __init__(self, evaluationStrategyFactory: FeatureFlagEvaluationStrategyFactory) -> None:
        self.evaluationStrategyFactory = evaluationStrategyFactory

    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        nestedConditions = self.extractNestedConditions(featureFlagEntity.conditionConfiguration)
        if not nestedConditions:
            return False

        logicalOperator = str(
            featureFlagEntity.conditionConfiguration.get("logical_operator") or "AND"
        ).upper()

        evaluationResults: List[bool] = []
        for nestedCondition in nestedConditions:
            nestedFeatureFlagEntity = self.buildNestedFeatureFlagEntity(
                featureFlagEntity,
                nestedCondition,
            )
            nestedStrategy = self.evaluationStrategyFactory.resolveStrategy(
                nestedFeatureFlagEntity.conditionType
            )
            evaluationResults.append(
                nestedStrategy.evaluateFeatureFlag(nestedFeatureFlagEntity, evaluationContext)
            )

        if logicalOperator == "OR":
            return any(evaluationResults)
        return all(evaluationResults)

    def extractNestedConditions(self, conditionConfiguration: Dict[str, Any]) -> List[Dict[str, Any]]:
        rawNestedConditions = conditionConfiguration.get("nested_conditions") or []
        return [dict(nestedCondition) for nestedCondition in rawNestedConditions]

    def buildNestedFeatureFlagEntity(
            self,
            parentFeatureFlagEntity: FeatureFlagEntity,
            nestedCondition: Dict[str, Any],
    ) -> FeatureFlagEntity:
        return FeatureFlagEntity(
            featureFlagId=parentFeatureFlagEntity.featureFlagId,
            featureName=parentFeatureFlagEntity.featureName,
            conditionType=FeatureFlagConditionType(str(nestedCondition["condition_type"])),
            conditionConfiguration=dict(nestedCondition.get("condition_configuration") or {}),
            defaultEnabled=parentFeatureFlagEntity.defaultEnabled,
            globallyEnabled=parentFeatureFlagEntity.globallyEnabled,
        )
