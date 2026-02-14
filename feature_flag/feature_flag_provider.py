from abc import ABC, abstractmethod


class FeatureFlagProvider(ABC):
    @abstractmethod
    def is_enabled(self, feature_key: str) -> bool:
        pass
