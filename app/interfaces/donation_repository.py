from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DonationRepository(ABC):
    @abstractmethod
    def create_campaign(self, masjid_id: str, created_by: str, data: dict) -> dict:
        pass

    @abstractmethod
    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_active_campaigns(self, masjid_id: str) -> List[dict]:
        pass

    @abstractmethod
    def update_campaign(self, campaign_id: str, updates: dict) -> dict:
        pass

    @abstractmethod
    def cancel_campaign(self, campaign_id: str) -> dict:
        pass

    @abstractmethod
    def create_donation(
        self, campaign_id: str, masjid_id: str, donor: dict, amount: int, payment_method: str
    ) -> dict:
        pass

    @abstractmethod
    def update_donation_status(
        self, donation_id: str, status: str, transaction_id: Optional[str]
    ) -> dict:
        pass

    @abstractmethod
    def get_donation(self, donation_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_campaign_donors(self, campaign_id: str, limit: int) -> List[dict]:
        pass

    @abstractmethod
    def get_user_donations(self, user_id: str, page: int, limit: int) -> dict:
        pass