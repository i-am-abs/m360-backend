from __future__ import annotations

from abc import ABC, abstractmethod


class PhoneValidator(ABC):
    @abstractmethod
    def validate_and_format(self, phone_number: str) -> str:
        pass
