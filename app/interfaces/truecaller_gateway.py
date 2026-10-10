from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict


class TruecallerFailure(str, Enum):
    EXCHANGE = "exchange"
    PROFILE = "profile"
    UNAVAILABLE = "unavailable"


class TruecallerGatewayError(Exception):
    def __init__(self, failure: TruecallerFailure) -> None:
        super().__init__(failure.value)
        self.failure = failure


class TruecallerGateway(ABC):
    @abstractmethod
    def exchange_code(self, authorization_code: str, code_verifier: str) -> str:
        pass

    @abstractmethod
    def fetch_profile(self, access_token: str) -> Dict[str, Any]:
        pass
