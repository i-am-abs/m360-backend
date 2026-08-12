from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ClaimRepository(ABC):
    @abstractmethod
    def create_claim(self, user_id: str, masjid_id: str, role: str, note: Optional[str]) -> dict:
        pass

    @abstractmethod
    def get_claim(self, claim_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_user_claim_for_masjid(self, user_id: str, masjid_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_claims(self, status: Optional[str], page: int, limit: int) -> dict:
        pass

    @abstractmethod
    def approve_claim(self, claim_id: str, reviewer_id: str, note: Optional[str]) -> dict:
        pass

    @abstractmethod
    def reject_claim(self, claim_id: str, reviewer_id: str, note: str) -> dict:
        pass
