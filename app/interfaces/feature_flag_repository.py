from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class FeatureFlagRepository(ABC):
    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        """Return all location feature-flag documents."""

    @abstractmethod
    def find_by_location_key(self, location_key: str) -> Optional[Dict[str, Any]]:
        """Return config for an exact location_key match."""

    @abstractmethod
    def find_by_coordinates(
        self,
        latitude: float,
        longitude: float,
    ) -> Optional[Dict[str, Any]]:
        """Return the best-matching config for lat/lng bounds."""

    @abstractmethod
    def find_by_region(
        self,
        country: Optional[str],
        state: Optional[str],
        city: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Return config matching country/state/city hierarchy."""
