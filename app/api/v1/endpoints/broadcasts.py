from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_broadcast_service,
    get_current_user,
    get_notification_service,
)
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.broadcast import BroadcastCreateRequest
from app.schemas.fcm import MasjidFollowResponse
from app.services.broadcast_service import BroadcastService
from app.services.notification_service import NotificationService
from app.utils.response import success_response

router = APIRouter(tags=["broadcast"])


@router.post(ApiEndpoint.MASJID_FOLLOW.value, summary="Follow a masjid for broadcasts")
def follow_masjid(
        place_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: NotificationService = Depends(get_notification_service),
):
    user_id = str(current_user["user_id"])
    svc.follow_masjid(user_id, place_id)
    response = MasjidFollowResponse(masjid_id=place_id, following=True)
    return success_response(response.model_dump(by_alias=True), message="Following masjid")


@router.delete(ApiEndpoint.MASJID_FOLLOW.value, summary="Unfollow a masjid")
def unfollow_masjid(
        place_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: NotificationService = Depends(get_notification_service),
):
    user_id = str(current_user["user_id"])
    svc.unfollow_masjid(user_id, place_id)
    response = MasjidFollowResponse(masjid_id=place_id, following=False)
    return success_response(response.model_dump(by_alias=True), message="Unfollowed masjid")


@router.get(ApiEndpoint.MASJID_BROADCASTS.value, summary="List masjid broadcasts (paginated, newest first)")
def list_broadcasts(
        place_id: str,
        limit: Optional[int] = Query(None, ge=1, le=100),
        before_id: Optional[int] = Query(None, ge=1, description="Cursor: last seen seq"),
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: BroadcastService = Depends(get_broadcast_service),
):
    page = svc.list_broadcasts(place_id, limit=limit, before_id=before_id)
    return success_response(page.model_dump(by_alias=True))


@router.post(ApiEndpoint.MASJID_BROADCASTS.value, summary="Create masjid broadcast (admin only)")
def create_broadcast(
        place_id: str,
        body: BroadcastCreateRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: BroadcastService = Depends(get_broadcast_service),
):
    result = svc.create_broadcast(place_id, body, current_user)
    return success_response(result.model_dump(by_alias=True), message="Broadcast created")
