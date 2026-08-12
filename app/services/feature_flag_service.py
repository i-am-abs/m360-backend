from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from app.core.enums.feature_flag import PlatformFeature
from app.interfaces.feature_flag_repository import FeatureFlagRepository
from app.services.feature_flag_strategies import (
    CoordinateStrategy,
    DefaultStrategy,
    FeatureResolutionStrategy,
    LocationKeyStrategy,
    LocationMatch,
    RegionStrategy,
    merge_features,
)
from app.utils.structured_log import log_event, log_timing

FeatureLike = Union[PlatformFeature, str]


@dataclass(frozen=True)
class FeatureResolution:
    """The location a request resolved to, plus the flags that location grants."""

    match: LocationMatch
    features: Dict[str, bool]

    @property
    def location_key(self) -> Optional[str]:
        return self.match.location_key

    @property
    def matched_by(self) -> str:
        return self.match.matched_by

    @property
    def document(self) -> Dict[str, Any]:
        return self.match.document

    def is_enabled(self, feature: PlatformFeature) -> bool:
        return bool(self.features.get(feature.value, False))


class FeatureFlagService:
    def __init__(self, store: FeatureFlagRepository) -> None:
        self._store = store
        self._strategies: list[FeatureResolutionStrategy] = [
            LocationKeyStrategy(store),
            CoordinateStrategy(store),
            RegionStrategy(store),
            DefaultStrategy(store),
        ]

    def resolve(self, **context: Any) -> FeatureResolution:
        # "level" is a reserved keyword of the logging helpers, not a location field.
        log_context = {key: value for key, value in context.items() if key != "level"}

        with log_timing("feature_flags", "resolve", **log_context):
            match = self._match(context)
            features = merge_features(match.document)
            if match.is_default:
                # Un-launched areas must not inherit launch-gated modules.
                for feature in PlatformFeature.launch_gated():
                    features[feature.value] = False

        log_event(
            "feature_flags",
            "resolved",
            # Outcome fields are namespaced so a request field such as
            # location_key cannot collide with the resolved value.
            resolved_location_key=match.location_key,
            resolved_by=match.matched_by,
            features=features,
            **log_context,
        )
        return FeatureResolution(match=match, features=features)

    def get_features(self, **context: Any) -> Dict[str, bool]:
        return self.resolve(**context).features

    def is_feature_enabled(self, feature: FeatureLike, **context: Any) -> bool:
        parsed = self._coerce(feature)
        if parsed is None:
            return False
        return self.resolve(**context).is_enabled(parsed)

    def is_masjid_region_enabled(self, **context: Any) -> bool:
        """True only when the user resolves to a non-default launched region."""
        return self.is_feature_enabled(PlatformFeature.MASJID_DISCOVERY, **context)

    def _match(self, context: Dict[str, Any]) -> LocationMatch:
        for strategy in self._strategies:
            match = strategy.resolve(context)
            if match is not None:
                return match
        return LocationMatch.unmatched()

    @staticmethod
    def _coerce(feature: FeatureLike) -> Optional[PlatformFeature]:
        if isinstance(feature, PlatformFeature):
            return feature
        return PlatformFeature.parse(feature)
