from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_verification_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.verification import VerificationRequestCreate
from app.schemas.verification_status import VerificationStatusUpdate
from app.services.verification_service import VerificationService
from app.utils.response import success_response

router = APIRouter(tags=["verification"])


@router.get(ApiEndpoint.ROLES.value, summary="List assignable verification roles")
def list_roles(svc: VerificationService = Depends(get_verification_service)):
    result = svc.list_roles()
    return success_response(result.model_dump())


@router.patch(
    ApiEndpoint.VERIFICATION_REQUEST_STATUS.value,
    summary="Approve or reject verification request (super_admin)",
)
def update_verification_status(
        request_id: str,
        body: VerificationStatusUpdate,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: VerificationService = Depends(get_verification_service),
):
    result = svc.update_status(request_id, body.status.value, current_user)
    return success_response(result.model_dump(by_alias=True), message="Status updated")


@router.post(ApiEndpoint.VERIFICATION_REQUESTS.value, summary="Submit verification request")
def create_verification_request(
        body: VerificationRequestCreate,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: VerificationService = Depends(get_verification_service),
):
    result = svc.create_request(body, current_user)
    return success_response(result.model_dump(by_alias=True), message="Verification request submitted")
