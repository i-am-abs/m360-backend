from __future__ import annotations

from typing import Dict, List

from app.modules.feature_flag.application.ports.feature_flag_evaluation_strategy_port import (
    FeatureFlagEvaluationStrategyPort,
)
from app.modules.feature_flag.infrastructure.strategies.environment_based_evaluation_strategy import (
    EnvironmentBasedEvaluationStrategy,
)
from app.modules.feature_flag.infrastructure.strategies.location_based_evaluation_strategy import (
    LocationBasedEvaluationStrategy,
)
from app.modules.feature_flag.infrastructure.strategies.percentage_rollout_evaluation_strategy import (
    PercentageRolloutEvaluationStrategy,
)
from app.modules.feature_flag.infrastructure.strategies.region_based_evaluation_strategy import (
    RegionBasedEvaluationStrategy,
)
from app.modules.feature_flag.infrastructure.strategies.time_based_evaluation_strategy import (
    TimeBasedEvaluationStrategy,
)
from app.modules.feature_flag.infrastructure.strategies.user_based_evaluation_strategy import (
    UserBasedEvaluationStrategy,
)


class FeatureFlagEvaluationStrategyFactory:
    def __init__(self) -> None:
        self.compositeEvaluationStrategy = None
        self.strategyRegistryByConditionType: Dict[str, FeatureFlagEvaluationStrategyPort] = (
            self.buildStrategyRegistry()
        )

    def buildStrategyRegistry(self) -> Dict[str, FeatureFlagEvaluationStrategyPort]:
        from app.modules.feature_flag.infrastructure.strategies.composite_evaluation_strategy import (
            CompositeEvaluationStrategy,
        )

        self.compositeEvaluationStrategy = CompositeEvaluationStrategy(self)
        registeredStrategies: List[FeatureFlagEvaluationStrategyPort] = [
            LocationBasedEvaluationStrategy(),
            UserBasedEvaluationStrategy(),
            EnvironmentBasedEvaluationStrategy(),
            RegionBasedEvaluationStrategy(),
            PercentageRolloutEvaluationStrategy(),
            TimeBasedEvaluationStrategy(),
            self.compositeEvaluationStrategy,
        ]
        return {
            evaluationStrategy.supportedConditionType: evaluationStrategy
            for evaluationStrategy in registeredStrategies
        }

    def resolveStrategy(
            self,
            conditionType: str,
    ) -> FeatureFlagEvaluationStrategyPort:
        evaluationStrategy = self.strategyRegistryByConditionType.get(conditionType)
        if evaluationStrategy is None:
            raise ValueError(f"No evaluation strategy registered for condition type '{conditionType}'.")
        return evaluationStrategy

    def registerStrategy(
            self,
            evaluationStrategy: FeatureFlagEvaluationStrategyPort,
    ) -> None:
        self.strategyRegistryByConditionType[evaluationStrategy.supportedConditionType] = evaluationStrategy
