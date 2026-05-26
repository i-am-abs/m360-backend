from __future__ import annotations

from typing import Any, Dict, Optional

from app.modules.feature_flag.application.dto.feature_flag_dto import (
    FeatureFlagCreateRequestDto,
    FeatureFlagEvaluationRequestDto,
    FeatureFlagUpdateRequestDto,
)
from app.modules.feature_flag.application.services.feature_flag_management_service import (
    FeatureFlagManagementService,
)
from app.modules.feature_flag.api.presenters.feature_flag_presenter import FeatureFlagPresenter


class FeatureFlagController:
    def __init__(self, featureFlagManagementService: FeatureFlagManagementService) -> None:
        self.featureFlagManagementService = featureFlagManagementService

    def createFeatureFlag(self, createRequest: FeatureFlagCreateRequestDto) -> Dict[str, Any]:
        featureFlagResponse = self.featureFlagManagementService.createFeatureFlag(createRequest)
        return FeatureFlagPresenter.toFeatureFlagView(featureFlagResponse)

    def updateFeatureFlag(
            self,
            featureName: str,
            updateRequest: FeatureFlagUpdateRequestDto,
    ) -> Dict[str, Any]:
        featureFlagResponse = self.featureFlagManagementService.updateFeatureFlag(
            featureName,
            updateRequest,
        )
        return FeatureFlagPresenter.toFeatureFlagView(featureFlagResponse)

    def deleteFeatureFlag(self, featureName: str) -> Dict[str, Any]:
        self.featureFlagManagementService.deleteFeatureFlag(featureName)
        return {"feature_name": featureName.strip().upper(), "deleted": True}

    def getFeatureFlagByName(self, featureName: str) -> Dict[str, Any]:
        featureFlagResponse = self.featureFlagManagementService.getFeatureFlagByName(featureName)
        return FeatureFlagPresenter.toFeatureFlagView(featureFlagResponse)

    def listAllFeatureFlags(self) -> Dict[str, Any]:
        featureFlagListResponse = self.featureFlagManagementService.listAllFeatureFlags()
        return FeatureFlagPresenter.toFeatureFlagListView(featureFlagListResponse)

    def evaluateFeatureFlag(
            self,
            evaluationRequest: FeatureFlagEvaluationRequestDto,
    ) -> Dict[str, Any]:
        evaluationResponse = self.featureFlagManagementService.evaluateFeatureFlag(evaluationRequest)
        return FeatureFlagPresenter.toFeatureFlagEvaluationView(evaluationResponse)

    def evaluateFeatureFlagByQueryParameters(
            self,
            featureName: str,
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
            userId: Optional[str] = None,
            environmentName: Optional[str] = None,
            regionCode: Optional[str] = None,
    ) -> Dict[str, Any]:
        evaluationRequest = FeatureFlagEvaluationRequestDto(
            feature_name=featureName,
            latitude=latitude,
            longitude=longitude,
            user_id=userId,
            environment_name=environmentName,
            region_code=regionCode,
        )
        return self.evaluateFeatureFlag(evaluationRequest)
