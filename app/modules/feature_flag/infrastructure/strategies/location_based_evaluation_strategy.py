from __future__ import annotations

from typing import Any, Dict, List

from app.modules.feature_flag.application.ports.feature_flag_evaluation_strategy_port import (
    FeatureFlagEvaluationStrategyPort,
)
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.value_objects.circular_geofence_region import CircularGeofenceRegion
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)
from app.modules.feature_flag.domain.value_objects.geographic_coordinate import GeographicCoordinate


class LocationBasedEvaluationStrategy(FeatureFlagEvaluationStrategyPort):
    supportedConditionType = "LOCATION"

    def evaluateFeatureFlag(
            self,
            featureFlagEntity: FeatureFlagEntity,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        if evaluationContext.latitude is None or evaluationContext.longitude is None:
            return False

        targetCoordinate = GeographicCoordinate(
            latitude=evaluationContext.latitude,
            longitude=evaluationContext.longitude,
        )
        allowedGeofenceRegions = self.buildAllowedGeofenceRegions(
            featureFlagEntity.conditionConfiguration
        )
        for geofenceRegion in allowedGeofenceRegions:
            if geofenceRegion.containsCoordinate(targetCoordinate):
                return True
        return False

    def buildAllowedGeofenceRegions(
            self,
            conditionConfiguration: Dict[str, Any],
    ) -> List[CircularGeofenceRegion]:
        rawRegions = conditionConfiguration.get("allowed_geofence_regions") or []
        geofenceRegions: List[CircularGeofenceRegion] = []
        for rawRegion in rawRegions:
            geofenceRegions.append(CircularGeofenceRegion.fromDictionary(rawRegion))
        return geofenceRegions
