from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.config.app_config import AppConfig
from feature_flag.feature_flag_provider import FeatureFlagProvider
from feature_flag.feature_keys import FeatureKeys
from masjid.masjid_repository import MasjidRepository
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class MasjidService:
    def __init__(
        self,
        repository: MasjidRepository,
        config: AppConfig,
        feature_flag_provider: FeatureFlagProvider,
    ):
        self._repository = repository
        self._config = config
        self._feature_flags = feature_flag_provider

    def find_nearby(
        self,
        longitude: float,
        latitude: float,
        radius_km: Optional[float] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        if not self._feature_flags.is_enabled(FeatureKeys.MASJID_LOCATION):
            return {
                "enabled": False,
                "message": "Masjid location search is not enabled for this environment (pilot testing).",
                "masjids": [],
                "count": 0,
                "radius_km": 0,
            }

        radius = radius_km if radius_km is not None else self._config.get_masjid_search_radius_km()
        masjids = self._repository.find_nearby(
            longitude=longitude,
            latitude=latitude,
            radius_km=radius,
            limit=limit,
        )
        return {
            "enabled": True,
            "masjids": masjids,
            "count": len(masjids),
            "radius_km": radius,
        }
