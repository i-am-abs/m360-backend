from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.core.enums.feature_flag import MatchSource, PlatformFeature
from app.interfaces.feature_flag_repository import FeatureFlagRepository

DEFAULT_LOCATION_KEY = "*"


@dataclass(frozen=True)
class LocationMatch:
    document: Dict[str, Any]
    matched_by: str

    @staticmethod
    def unmatched() -> "LocationMatch":
        return LocationMatch(document={}, matched_by=MatchSource.NONE.value)

    @property
    def location_key(self) -> Optional[str]:
        return self.document.get("location_key") or None

    @property
    def is_default(self) -> bool:
        """True when no launched region applies, so launch-gated flags stay off."""
        return not self.document or self.location_key == DEFAULT_LOCATION_KEY


class FeatureResolutionStrategy(ABC):
    def __init__(self, store: FeatureFlagRepository) -> None:
        self._store = store

    @abstractmethod
    def resolve(self, context: Dict[str, Any]) -> Optional[LocationMatch]:
        pass

    @staticmethod
    def _wrap(
            doc: Optional[Dict[str, Any]],
            matched_by: MatchSource,
    ) -> Optional[LocationMatch]:
        if not doc:
            return None
        return LocationMatch(document=doc, matched_by=matched_by.value)


class LocationKeyStrategy(FeatureResolutionStrategy):
    def resolve(self, context: Dict[str, Any]) -> Optional[LocationMatch]:
        key = context.get("location_key")
        if not key:
            return None
        return self._wrap(
            self._store.find_by_location_key(str(key)),
            MatchSource.LOCATION_KEY,
        )


class CoordinateStrategy(FeatureResolutionStrategy):
    def resolve(self, context: Dict[str, Any]) -> Optional[LocationMatch]:
        latitude = context.get("latitude")
        longitude = context.get("longitude")
        if latitude is None or longitude is None:
            return None
        try:
            lat = float(latitude)
            lng = float(longitude)
        except (TypeError, ValueError):
            return None
        return self._wrap(
            self._store.find_by_coordinates(lat, lng),
            MatchSource.COORDINATES,
        )


class RegionStrategy(FeatureResolutionStrategy):
    def resolve(self, context: Dict[str, Any]) -> Optional[LocationMatch]:
        country = context.get("country")
        if not country:
            return None
        return self._wrap(
            self._store.find_by_region(
                country,
                context.get("state"),
                context.get("city"),
            ),
            MatchSource.REGION,
        )


class DefaultStrategy(FeatureResolutionStrategy):
    def resolve(self, context: Dict[str, Any]) -> Optional[LocationMatch]:
        return self._wrap(
            self._store.find_by_location_key(DEFAULT_LOCATION_KEY),
            MatchSource.DEFAULT,
        )


def merge_features(doc: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    defaults = PlatformFeature.default_flags()
    if not doc:
        return defaults
    stored = doc.get("features") or {}
    for key in PlatformFeature.values():
        if key in stored:
            defaults[key] = bool(stored[key])
    return defaults
