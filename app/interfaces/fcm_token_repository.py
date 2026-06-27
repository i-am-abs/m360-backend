from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class FcmTokenRepository(ABC):
    @abstractmethod
    def register(self, user_id: str, token: str, platform: str | None = None) -> None:
        pass

    @abstractmethod
    def list_tokens_for_users(self, user_ids: List[str]) -> List[str]:
        pass

    @abstractmethod
    def remove(self, token: str) -> None:
        pass
