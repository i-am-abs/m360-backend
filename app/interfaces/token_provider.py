from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class TokenProvider(ABC):
    @abstractmethod
    def get_access_token(self) -> str:
        pass

    @abstractmethod
    def clear_token(self) -> None:
        pass

    @property
    @abstractmethod
    def access_token(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def expiry(self) -> Optional[datetime]:
        pass
