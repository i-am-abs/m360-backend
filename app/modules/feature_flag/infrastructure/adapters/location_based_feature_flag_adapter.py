from __future__ import annotations

from app.modules.feature_flag.application.services.feature_flag_management_service import (
    FeatureFlagManagementService,
)


class LocationBasedFeatureFlagAdapter:
    def __init__(self, featureFlagManagementService: FeatureFlagManagementService) -> None:
        self.featureFlagManagementService = featureFlagManagementService

    def isFeatureEnabledAtLocation(
            self,
            featureName: str,
            latitude: float,
            longitude: float,
    ) -> bool:
        return self.featureFlagManagementService.isFeatureEnabledAtLocation(
            featureName,
            latitude,
            longitude,
        )
