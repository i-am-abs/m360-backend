from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_admin_service, get_current_user, get_optional_current_user
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.admin import AdminRegisterRequest, AdminStatusUpdateRequest
from app.services.admin_service import AdminService
from app.utils.response import success_response

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


@router.get(ApiEndpoint.ADMINS_LIST.value, summary="List admin registrations")
def list_admins(
        status: Optional[str] = Query(None),
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: AdminService = Depends(get_admin_service),
):
    results = svc.list_admins(current_user, status=status)
    return success_response([item.model_dump(by_alias=True) for item in results])
