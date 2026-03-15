from typing import Any, Dict, List, Optional, Set

from config.feature_flag_config import (
    get_flag_config_from_env,
    load_feature_flags_from_file,
    normalize_city_for_comparison,
)
from feature_flags.feature_context import FeatureContext
from feature_flags.feature_flag_provider import FeatureFlagProvider


class ConfigFeatureFlagProvider(FeatureFlagProvider):
    def __init__(self) -> None:
        self._file_config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        self._file_config = load_feature_flags_from_file()

    def _get_flag_config(self, flag_name: str) -> Dict[str, Any]:
        file_cfg = self._file_config.get(flag_name) or {}
        env_overrides = get_flag_config_from_env(flag_name)
        return {**file_cfg, **env_overrides}

    def is_enabled(
        self,
        flag_name: str,
        context: Optional[FeatureContext] = None,
    ) -> bool:
        config = self._get_flag_config(flag_name)
        enabled = config.get("enabled", True)
        if not enabled:
            return False

        enabled_cities: Optional[List[str]] = config.get("enabled_cities")
        if not enabled_cities:
            return True

        city_set: Set[str] = {
            normalize_city_for_comparison(c) for c in enabled_cities if c
        }
        city_set.discard(None)

        if not city_set:
            return True

        context_city: Optional[str] = None
        if context:
            context_city = normalize_city_for_comparison(context.city)
        if not context_city:
            return False
        return context_city in city_set
