from typing import Optional

from feature_flags.feature_context import FeatureContext
from feature_flags.feature_flag_provider import FeatureFlagProvider


class MongoFeatureFlagProvider(FeatureFlagProvider):
    def __init__(self) -> None:
        self._collection = None

    def is_enabled(
        self,
        flag_name: str,
        context: Optional[FeatureContext] = None,
    ) -> bool:
        if self._collection is None:
            return True
        raise NotImplementedError(
            "MongoDB feature flag not wired; use ConfigFeatureFlagProvider or implement this."
        )
