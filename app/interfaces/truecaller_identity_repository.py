from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TruecallerIdentityConflict(Exception):
    """The Truecaller identity is already bound to a different phone number."""


class TruecallerIdentityRepository(ABC):
    @abstractmethod
    def find_by_sub(self, sub: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def link(self, sub: str, user_id: str, phone_number: str) -> None:
        """Bind ``sub`` to ``phone_number`` (idempotent); raise TruecallerIdentityConflict
        if ``sub`` is already bound to another phone number."""
