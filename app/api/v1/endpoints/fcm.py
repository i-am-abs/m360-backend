from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services.fcm_service import FcmService

router = APIRouter(tags=["fcm"])


class FcmTokenRequest(BaseModel):
    token: str


@router.post("/users/fcm-token")
def register_fcm_token(
    request: Request,
    body: FcmTokenRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    fcm: FcmService = getattr(request.app.state, "fcm_service", None)
    if fcm:
        fcm.store_token(current_user["user_id"], body.token)
    return {"status": "ok"}
