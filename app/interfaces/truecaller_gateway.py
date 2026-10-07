from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class TruecallerGateway(ABC):
    @abstractmethod
    def exchange_code(self, authorization_code: str, code_verifier: str) -> str:
        pass

    @abstractmethod
    def fetch_profile(self, access_token: str) -> Dict[str, Any]:
        pass
