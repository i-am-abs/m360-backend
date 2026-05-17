from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheStore(ABC):
    @abstractmethod
    def get_json(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def ping(self) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
