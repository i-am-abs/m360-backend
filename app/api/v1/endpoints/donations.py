from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_user, get_donation_service, get_masjid_entity_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.exceptions.base import ApiException
from app.schemas.donation import CampaignCreate, CampaignUpdate, DonationInitiate
from app.services.donation_service import DonationService
from app.services.masjid_entity_service import MasjidEntityService
from app.utils.response import success_response

router = APIRouter(tags=["donations"])


def _require_committee(masjid_id: str, user_id: str, masjid_svc: MasjidEntityService) -> None:
    masjid = masjid_svc.get_masjid(masjid_id)
    masjid_data = masjid.get("masjid", {})
    committee = masjid_data.get("management", {}).get("committee", [])
    if not any(m.get("user_id") == user_id for m in committee):
        raise ApiException("Only committee members can perform this action", status_code=HTTPStatus.FORBIDDEN)


@router.post(ApiEndpoint.CAMPAIGN_CREATE.value, summary="Create campaign")
def create_campaign(
    masjid_id: str,
    req: CampaignCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    donation_svc: DonationService = Depends(get_donation_service),
    masjid_svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    _require_committee(masjid_id, current_user["user_id"], masjid_svc)
    campaign = donation_svc.create_campaign(masjid_id, current_user["user_id"], req.model_dump())
    return success_response({"campaign": campaign})


@router.get(ApiEndpoint.CAMPAIGN_LIST.value, summary="List active campaigns")
def list_campaigns(
    masjid_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
):
    campaigns = svc.get_active_campaigns(masjid_id)
    return success_response({"campaigns": campaigns})


@router.get(ApiEndpoint.CAMPAIGN_GET.value, summary="Get campaign detail")
def get_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
):
    return success_response(svc.get_campaign(campaign_id))


@router.put(ApiEndpoint.CAMPAIGN_UPDATE.value, summary="Update campaign")
def update_campaign(
    campaign_id: str,
    req: CampaignUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
    masjid_svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    campaign = svc._donation_repo.get_campaign(campaign_id)
    if not campaign:
        raise ApiException("Campaign not found", status_code=HTTPStatus.NOT_FOUND)
    _require_committee(campaign.get("masjid_id", ""), current_user["user_id"], masjid_svc)
    result = svc.update_campaign(campaign_id, req.model_dump(exclude_none=True))
    return success_response(result)


@router.delete(ApiEndpoint.CAMPAIGN_CANCEL.value, summary="Cancel campaign")
def cancel_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
    masjid_svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    campaign = svc._donation_repo.get_campaign(campaign_id)
    if not campaign:
        raise ApiException("Campaign not found", status_code=HTTPStatus.NOT_FOUND)
    _require_committee(campaign.get("masjid_id", ""), current_user["user_id"], masjid_svc)
    result = svc.cancel_campaign(campaign_id)
    return success_response(result)


@router.post(ApiEndpoint.DONATION_INITIATE.value, summary="Initiate donation")
def initiate_donation(
    campaign_id: str,
    req: DonationInitiate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
):
    result = svc.initiate_donation(
        campaign_id, current_user["user_id"], req.amount, req.payment_method, req.is_anonymous,
    )
    return success_response(result)


@router.get(ApiEndpoint.DONATION_STATUS.value, summary="Donation status")
def donation_status(
    donation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
):
    return success_response(svc.get_donation_status(donation_id))


@router.get(ApiEndpoint.DONATION_HISTORY.value, summary="User donation history")
def donation_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
):
    return success_response(svc.get_user_donations(current_user["user_id"], page, limit))


@router.get(ApiEndpoint.CAMPAIGN_DONORS.value, summary="Campaign donors")
def campaign_donors(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: DonationService = Depends(get_donation_service),
):
    campaign = svc._donation_repo.get_campaign(campaign_id)
    if not campaign:
        raise ApiException("Campaign not found", status_code=HTTPStatus.NOT_FOUND)
    donors = svc._donation_repo.get_campaign_donors(campaign_id, 50)
    return success_response({"donors": donors})


@router.post(ApiEndpoint.PAYMENT_WEBHOOK.value, summary="Payment webhook")
async def payment_webhook(
    request: Request,
    svc: DonationService = Depends(get_donation_service),
):
    body = await request.json()
    event = body.get("event", "")
    if event == "payment.captured":
        payment = body.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment.get("order_id", "")
        txn_id = payment.get("id", "")
        donation_id = order_id.replace("order_", "") if order_id else ""
        if donation_id:
            svc.confirm_donation(donation_id, txn_id)
    return success_response({"received": True})