from abc import ABC, abstractmethod
from typing import Optional

from feature_flags.feature_context import FeatureContext


class FeatureFlagProvider(ABC):
    @abstractmethod
    def is_enabled(
        self,
        flag_name: str,
        context: Optional[FeatureContext] = None,
    ) -> bool:
        pass
