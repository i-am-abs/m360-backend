from __future__ import annotations

from typing import Any, Dict

from app.modules.feature_flag.application.dto.feature_flag_dto import (
    FeatureFlagEvaluationResponseDto,
    FeatureFlagListResponseDto,
    FeatureFlagResponseDto,
)


class FeatureFlagPresenter:
    @staticmethod
    def toFeatureFlagView(featureFlagResponse: FeatureFlagResponseDto) -> Dict[str, Any]:
        return featureFlagResponse.model_dump(mode="json")

    @staticmethod
    def toFeatureFlagListView(featureFlagListResponse: FeatureFlagListResponseDto) -> Dict[str, Any]:
        return {
            "count": featureFlagListResponse.count,
            "feature_flags": [
                FeatureFlagPresenter.toFeatureFlagView(featureFlagResponse)
                for featureFlagResponse in featureFlagListResponse.feature_flags
            ],
        }

    @staticmethod
    def toFeatureFlagEvaluationView(
            evaluationResponse: FeatureFlagEvaluationResponseDto,
    ) -> Dict[str, Any]:
        return evaluationResponse.model_dump(mode="json")
