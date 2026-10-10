from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_admin_service, get_current_user, get_optional_current_user
from app.api.v1.model.admin_status_model import AdminStatusUpdateRequest
from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.admin import AdminRegisterRequest
from app.services.admin_service import AdminService
from app.utils.response import no_store, success_response

router = APIRouter(tags=["admins"])


@router.post(ApiEndpoint.ADMINS_REGISTER.value, summary="Register admin or committee member")
def register_admin(
        body: AdminRegisterRequest,
        current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
        svc: AdminService = Depends(get_admin_service),
):
    result = svc.register(body, current_user=current_user)
    return success_response(result.model_dump(by_alias=True), message="Registration submitted")


@router.patch(ApiEndpoint.ADMINS_STATUS.value, summary="Approve or reject admin registration")
def update_admin_status(
        admin_id: str,
        body: AdminStatusUpdateRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: AdminService = Depends(get_admin_service),
):
    result = svc.update_status(admin_id, body, current_user)
    return success_response(result.model_dump(by_alias=True), message="Status updated")


@router.get(ApiEndpoint.ADMINS_LIST.value, summary="List approved admins")
def list_admins(
        status: Optional[str] = Query(
            None,
            description=(
                    "Filter by status (approved|pending). "
                    "Omit to return approved admins. Rejected requests are never listed."
            ),
        ),
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: AdminService = Depends(get_admin_service),
):
    return no_store(success_response(svc.list_admins(current_user, status=status)))


@router.get(ApiEndpoint.ADMINS_PENDING.value, summary="List pending admin requests")
def list_pending_admins(
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: AdminService = Depends(get_admin_service),
):
    return no_store(success_response(
        svc.list_admins(current_user, status=AdminRegistrationStatus.PENDING.value),
    ))
