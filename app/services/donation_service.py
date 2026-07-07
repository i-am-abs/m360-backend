from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.donation_repository import DonationRepository
from app.services.broadcast_service import BroadcastService

log = get_logger(__name__)


class DonationService:
    def __init__(
        self,
        donation_repo: DonationRepository,
        broadcast_service: BroadcastService,
    ) -> None:
        self._donation_repo = donation_repo
        self._broadcast_service = broadcast_service

    def create_campaign(self, masjid_id: str, created_by: str, data: Dict[str, Any]) -> Dict[str, Any]:
        campaign = self._donation_repo.create_campaign(masjid_id, created_by, data)
        try:
            self._broadcast_service.post_campaign_card(masjid_id, campaign)
        except Exception as e:
            log.warning("Failed to auto-post campaign card: %s", e)
        log.info("Campaign created: masjidId=%s createdBy=%s title=%s", masjid_id, created_by, data.get("title"))
        return campaign

    def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        campaign = self._donation_repo.get_campaign(campaign_id)
        if not campaign:
            raise ApiException("Campaign not found", status_code=HTTPStatus.NOT_FOUND)
        donors = self._donation_repo.get_campaign_donors(campaign_id, 20)
        return {
            "campaign": campaign,
            "recent_donors": donors,
            "total_donors": campaign.get("donor_count", len(donors)),
        }

    def get_active_campaigns(self, masjid_id: str) -> list:
        return self._donation_repo.get_active_campaigns(masjid_id)

    def update_campaign(self, campaign_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        campaign = self._donation_repo.get_campaign(campaign_id)
        if not campaign:
            raise ApiException("Campaign not found", status_code=HTTPStatus.NOT_FOUND)

        if "target_amount" in updates:
            raised = campaign.get("raised_amount", 0)
            if updates["target_amount"] < raised:
                raise ApiException(
                    "Cannot reduce target below already raised amount",
                    status_code=HTTPStatus.BAD_REQUEST,
                )

        return self._donation_repo.update_campaign(campaign_id, updates)

    def cancel_campaign(self, campaign_id: str) -> Dict[str, Any]:
        campaign = self._donation_repo.get_campaign(campaign_id)
        if not campaign:
            raise ApiException("Campaign not found", status_code=HTTPStatus.NOT_FOUND)
        return self._donation_repo.cancel_campaign(campaign_id)

    def initiate_donation(
        self,
        campaign_id: str,
        user_id: str,
        amount: int,
        payment_method: str,
        is_anonymous: bool = False,
    ) -> Dict[str, Any]:
        campaign = self._donation_repo.get_campaign(campaign_id)
        if not campaign:
            raise ApiException("Campaign not found", status_code=HTTPStatus.NOT_FOUND)
        if campaign.get("status") != "active":
            raise ApiException("Campaign is not active", status_code=HTTPStatus.BAD_REQUEST)

        masjid_id = campaign.get("masjid_id", "")
        donor = {"user_id": user_id, "name": "Donor"}
        donation = self._donation_repo.create_donation(campaign_id, masjid_id, donor, amount, payment_method)

        log.info("Donation initiated: campaignId=%s userId=%s amount=%s", campaign_id, user_id, amount)
        return {
            "donation": {
                "id": str(donation.get("_id", donation.get("id", ""))),
                "payment_status": donation.get("payment_status", "pending"),
            },
            "payment": {
                "order_id": f"order_{donation.get('_id', donation.get('id', ''))}",
                "amount": amount,
            },
        }

    def confirm_donation(self, donation_id: str, transaction_id: str) -> Dict[str, Any]:
        donation = self._donation_repo.get_donation(donation_id)
        if not donation:
            raise ApiException("Donation not found", status_code=HTTPStatus.NOT_FOUND)

        donation = self._donation_repo.update_donation_status(donation_id, "completed", transaction_id)

        campaign_id = donation.get("campaign_id")
        if campaign_id:
            campaign = self._donation_repo.get_campaign(campaign_id)
            if campaign:
                raised = campaign.get("raised_amount", 0) + donation.get("amount", 0)
                donor_count = campaign.get("donor_count", 0) + 1
                self._donation_repo.update_campaign(campaign_id, {
                    "raised_amount": raised,
                    "donor_count": donor_count,
                })

        log.info("Donation confirmed: donationId=%s transactionId=%s", donation_id, transaction_id)
        return donation

    def get_donation_status(self, donation_id: str) -> Dict[str, Any]:
        donation = self._donation_repo.get_donation(donation_id)
        if not donation:
            raise ApiException("Donation not found", status_code=HTTPStatus.NOT_FOUND)
        return {
            "donation": {
                "id": str(donation.get("_id", donation.get("id", ""))),
                "payment_status": donation.get("payment_status"),
                "transaction_id": donation.get("transaction_id"),
                "amount": donation.get("amount"),
            }
        }

    def get_user_donations(self, user_id: str, page: int, limit: int) -> Dict[str, Any]:
        return self._donation_repo.get_user_donations(user_id, page, limit)