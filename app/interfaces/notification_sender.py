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
        """Send a push notification to many device tokens.

        Returns ``(sent_count, failed_count, invalid_tokens)`` where
        ``invalid_tokens`` should be pruned from storage by the caller.
        """
