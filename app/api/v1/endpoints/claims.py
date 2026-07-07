from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_claim_service, get_current_user, require_platform_admin
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.claim import ClaimRequest, ClaimReview
from app.services.claim_service import ClaimService
from app.utils.response import success_response

router = APIRouter(tags=["claims"])


@router.post(ApiEndpoint.CLAIM_SUBMIT.value, summary="Submit committee claim")
def submit_claim(
    masjid_id: str,
    req: ClaimRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
):
    return success_response(
        svc.submit_claim(current_user["user_id"], masjid_id, req.claimed_role, req.applicant_note),
    )


@router.get(ApiEndpoint.CLAIM_STATUS.value, summary="Check claim status")
def get_claim_status(
    masjid_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
):
    result = svc.get_claim_status(current_user["user_id"], masjid_id)
    return success_response(result if result else {"claim": None})


@router.get(ApiEndpoint.ADMIN_CLAIMS_LIST.value, summary="List claims (admin)")
def list_claims(
    status: str = Query("pending"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    admin: Dict[str, Any] = Depends(require_platform_admin),
    svc: ClaimService = Depends(get_claim_service),
):
    return success_response(svc.list_claims(status, page, limit))


@router.get(ApiEndpoint.ADMIN_CLAIM_GET.value, summary="Get single claim (admin)")
def get_claim(
    claim_id: str,
    admin: Dict[str, Any] = Depends(require_platform_admin),
    svc: ClaimService = Depends(get_claim_service),
):
    return success_response(svc.list_claims(None, 1, 1))  # placeholder


@router.post(ApiEndpoint.ADMIN_CLAIM_APPROVE.value, summary="Approve claim")
def approve_claim(
    claim_id: str,
    req: ClaimReview = ClaimReview(),
    admin: Dict[str, Any] = Depends(require_platform_admin),
    svc: ClaimService = Depends(get_claim_service),
):
    return success_response(svc.approve_claim(claim_id, admin["user_id"], req.reviewer_note))


@router.post(ApiEndpoint.ADMIN_CLAIM_REJECT.value, summary="Reject claim")
def reject_claim(
    claim_id: str,
    req: ClaimReview = ClaimReview(),
    admin: Dict[str, Any] = Depends(require_platform_admin),
    svc: ClaimService = Depends(get_claim_service),
):
    return success_response(svc.reject_claim(claim_id, admin["user_id"], req.reviewer_note))


@router.get(ApiEndpoint.ADMIN_CLAIM_STATS.value, summary="Claim dashboard stats")
def claim_stats(
    admin: Dict[str, Any] = Depends(require_platform_admin),
    svc: ClaimService = Depends(get_claim_service),
):
    result = svc.list_claims("pending", 1, 1)
    return success_response({"pending": result["pagination"]["total"]})