from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_optional_current_user, get_share_service
from app.schemas.share import ShareCreateRequest
from app.utils.response import success_response

router = APIRouter(tags=["Shares"])


@router.post("/shares", summary="Create a tracked share link")
def create_share(
    payload: ShareCreateRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    svc=Depends(get_share_service),
):
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Share service not available",
        )
    user_id = current_user["user_id"] if current_user else None
    data = svc.create_share(
        message_id=payload.message_id,
        parent_share_id=payload.parent_share_id,
        channel=payload.channel,
        platform=payload.platform,
        user_id=user_id,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
    )
    return success_response(data, message="Share link created", status_code=201)
