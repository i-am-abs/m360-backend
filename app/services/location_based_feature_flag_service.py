from app.modules.feature_flag.domain.value_objects.circular_geofence_region import CircularGeofenceRegion
from app.modules.feature_flag.domain.value_objects.geographic_coordinate import GeographicCoordinate
from app.modules.feature_flag.infrastructure.adapters.location_based_feature_flag_adapter import (
    LocationBasedFeatureFlagAdapter as LocationBasedFeatureFlagService,
)

__all__ = [
    "CircularGeofenceRegion",
    "FeatureFlagRule",
    "GeographicCoordinate",
    "LocationBasedFeatureFlagService",
]


class FeatureFlagRule:
    def __init__(self, featureName: str, allowedRegions, defaultEnabled: bool = False) -> None:
        self.featureName = featureName
        self.allowedRegions = allowedRegions
        self.defaultEnabled = defaultEnabled
