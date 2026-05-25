from __future__ import annotations

from typing import List

from app.modules.feature_flag.application.ports.feature_flag_repository_port import FeatureFlagRepositoryPort
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.enums.feature_flag_condition_type import FeatureFlagConditionType


class DefaultFeatureFlagSeedProvider:
    FEATURE_NAME_MASJID_SEARCH = "MASJID_SEARCH_FEATURE"
    FEATURE_NAME_DONATIONS = "DONATIONS_FEATURE"
    FEATURE_NAME_ANNOUNCEMENTS = "ANNOUNCEMENTS_FEATURE"

    def buildDefaultFeatureFlagEntities(self) -> List[FeatureFlagEntity]:
        return [
            FeatureFlagEntity(
                featureName=self.FEATURE_NAME_MASJID_SEARCH,
                displayName="Masjid Search",
                description="Enables nearby masjid search within configured geofence regions.",
                defaultEnabled=False,
                conditionType=FeatureFlagConditionType.LOCATION,
                conditionConfiguration={
                    "allowed_geofence_regions": [
                        {
                            "center_latitude": 20.0,
                            "center_longitude": 78.0,
                            "radius_in_meters": 2_500_000.0,
                        }
                    ]
                },
            ),
            FeatureFlagEntity(
                featureName=self.FEATURE_NAME_DONATIONS,
                displayName="Donations",
                description="Enables donation capabilities for masjids in configured geofence regions.",
                defaultEnabled=False,
                conditionType=FeatureFlagConditionType.LOCATION,
                conditionConfiguration={
                    "allowed_geofence_regions": [
                        {
                            "center_latitude": 19.0,
                            "center_longitude": 73.0,
                            "radius_in_meters": 200_000.0,
                        }
                    ]
                },
            ),
            FeatureFlagEntity(
                featureName=self.FEATURE_NAME_ANNOUNCEMENTS,
                displayName="Announcements",
                description="Enables announcement capabilities for masjids in configured geofence regions.",
                defaultEnabled=False,
                conditionType=FeatureFlagConditionType.LOCATION,
                conditionConfiguration={
                    "allowed_geofence_regions": [
                        {
                            "center_latitude": 28.6,
                            "center_longitude": 77.2,
                            "radius_in_meters": 300_000.0,
                        }
                    ]
                },
            ),
        ]

    def seedFeatureFlagsIfEmpty(self, featureFlagRepository: FeatureFlagRepositoryPort) -> int:
        if featureFlagRepository.countFeatureFlags() > 0:
            return 0

        seededCount = 0
        for featureFlagEntity in self.buildDefaultFeatureFlagEntities():
            featureFlagRepository.saveFeatureFlag(featureFlagEntity)
            seededCount += 1
        return seededCount
