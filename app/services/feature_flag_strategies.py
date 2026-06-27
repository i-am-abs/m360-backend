from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.core.enums.feature_flag import PlatformFeature
from app.interfaces.feature_flag_repository import FeatureFlagRepository


class FeatureResolutionStrategy(ABC):
    @abstractmethod
    def resolve(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass


class LocationKeyStrategy(FeatureResolutionStrategy):
    def __init__(self, store: FeatureFlagRepository) -> None:
        self._store = store

    def resolve(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = context.get("location_key")
        if not key:
            return None
        return self._store.find_by_location_key(key)


class CoordinateStrategy(FeatureResolutionStrategy):
    def __init__(self, store: FeatureFlagRepository) -> None:
        self._store = store

    def resolve(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        lat = context.get("latitude")
        lng = context.get("longitude")
        if lat is None or lng is None:
            return None
        return self._store.find_by_coordinates(float(lat), float(lng))


class RegionStrategy(FeatureResolutionStrategy):
    def __init__(self, store: FeatureFlagRepository) -> None:
        self._store = store

    def resolve(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        country = context.get("country")
        state = context.get("state")
        city = context.get("city")
        if not country:
            return None
        return self._store.find_by_region(country, state, city)


class DefaultStrategy(FeatureResolutionStrategy):
    def __init__(self, store: FeatureFlagRepository) -> None:
        self._store = store

    def resolve(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._store.find_by_location_key("*")


def merge_features(doc: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    defaults = PlatformFeature.default_flags()
    if not doc:
        return defaults
    stored = doc.get("features") or {}
    for key in PlatformFeature.values():
        if key in stored:
            defaults[key] = bool(stored[key])
    return defaults
