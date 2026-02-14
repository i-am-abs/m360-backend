import os

from feature_flag.feature_flag_provider import FeatureFlagProvider


class EnvFeatureFlagProvider(FeatureFlagProvider):
    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix.upper() + "_" if prefix else ""

    def is_enabled(self, feature_key: str) -> bool:
        key = f"{self._prefix}{feature_key.upper()}_ENABLED"
        val = os.getenv(key, "false").lower()
        return val in ("true", "1", "yes")
