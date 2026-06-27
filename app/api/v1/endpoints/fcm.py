from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_notification_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.fcm import FcmTokenRegisterRequest, FcmTokenResponse
from app.services.notification_service import NotificationService
from app.utils.response import success_response

router = APIRouter(tags=["broadcast"])


@router.post(ApiEndpoint.FCM_TOKENS.value, summary="Register FCM device token for current user")
def register_fcm_token(
        body: FcmTokenRegisterRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: NotificationService = Depends(get_notification_service),
):
    user_id = str(current_user["user_id"])
    svc.register_token(user_id, body.token, body.platform)
    response = FcmTokenResponse(user_id=user_id, token_registered=True)
    return success_response(response.model_dump(by_alias=True), message="Token registered")
