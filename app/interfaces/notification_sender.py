from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class NotificationSender(ABC):
    @abstractmethod
    def send_to_tokens(
            self,
            tokens: List[str],
            title: str,
            body: str,
            data: Dict[str, str] | None = None,
    ) -> Tuple[int, int, List[str]]:
        pass
