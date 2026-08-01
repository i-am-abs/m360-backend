from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_broadcast_feed_service, get_current_user, get_masjid_entity_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.exceptions.base import ApiException
from app.schemas.broadcast_feed import BroadcastMessageCreate, CampaignCardCreate, ReactionToggle
from app.services.broadcast_feed_service import BroadcastFeedService
from app.services.connection_manager import ConnectionManager
from app.services.masjid_entity_service import MasjidEntityService
from app.utils.response import success_response

router = APIRouter(tags=["broadcast"])


@router.get("/broadcast/public/{message_id}", summary="Get public broadcast")
def get_public_broadcast(
    message_id: str,
    svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
    masjid_svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    msg = svc.get_message_raw(message_id)
    masjid = masjid_svc.get_masjid(msg["masjid_id"])
    masjid_data = masjid.get("masjid", {}) if masjid else {}
    return success_response({
        "message": msg,
        "masjid": {
            "name": masjid_data.get("name", ""),
            "city": masjid_data.get("city", ""),
            "address": masjid_data.get("address", ""),
        },
    })


@router.get(ApiEndpoint.BROADCAST_LIST.value, summary="Get broadcast feed")
def get_broadcast_feed(
    masjid_id: str,
    cursor: Optional[datetime] = Query(None),
    since: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
):
    return success_response(svc.get_feed(masjid_id, cursor, since, limit, user_id=current_user["user_id"]))


@router.post(ApiEndpoint.BROADCAST_POST.value, summary="Post message")
def post_broadcast_message(
    masjid_id: str,
    req: BroadcastMessageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    broadcast_svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
    masjid_svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    masjid = masjid_svc.get_masjid(masjid_id)
    masjid_data = masjid.get("masjid", {})
    committee = masjid_data.get("management", {}).get("committee", [])
    sender_info = None
    for m in committee:
        if m.get("user_id") == current_user["user_id"]:
            sender_info = {"user_id": m["user_id"], "name": m.get("name", ""), "role": m.get("role", "")}
            break
    if not sender_info:
        raise ApiException("Only committee members can post", status_code=HTTPStatus.FORBIDDEN)

    if req.message_type == "video" and not req.video_url and not req.mux_asset_id and not req.mux_upload_id:
        raise ApiException("video_url, mux_asset_id, or mux_upload_id is required for video messages", status_code=HTTPStatus.BAD_REQUEST)
    if req.message_type == "campaign_card" and not req.campaign_id:
        raise ApiException("campaign_id is required for campaign_card messages", status_code=HTTPStatus.BAD_REQUEST)

    message = broadcast_svc.post_message(masjid_id, sender_info, req.model_dump())
    return success_response(message)


@router.post(ApiEndpoint.BROADCAST_POST.value + "/campaign-card", summary="Post campaign card to broadcast")
def post_campaign_card(
    masjid_id: str,
    req: CampaignCardCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    broadcast_svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
    masjid_svc: MasjidEntityService = Depends(get_masjid_entity_service),
):
    masjid = masjid_svc.get_masjid(masjid_id)
    masjid_data = masjid.get("masjid", {})
    committee = masjid_data.get("management", {}).get("committee", [])
    sender_info = None
    for m in committee:
        if m.get("user_id") == current_user["user_id"]:
            sender_info = {"user_id": m["user_id"], "name": m.get("name", ""), "role": m.get("role", "")}
            break
    if not sender_info:
        raise ApiException("Only committee members can post", status_code=HTTPStatus.FORBIDDEN)

    message = broadcast_svc.post_campaign_card(masjid_id, {"id": req.campaign_id, "text": req.text})
    return success_response(message)


@router.delete(ApiEndpoint.BROADCAST_DELETE.value, summary="Delete message")
def delete_broadcast_message(
    message_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
):
    svc.delete_message(message_id, current_user["user_id"])
    return success_response({"deleted": True})


@router.post(ApiEndpoint.BROADCAST_REACT.value, summary="React to message")
def react_to_message(
    message_id: str,
    req: ReactionToggle,
    current_user: Dict[str, Any] = Depends(get_current_user),
    svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
):
    result = svc.toggle_reaction(message_id, current_user["user_id"], req.emoji)
    return success_response(result)


@router.post("/broadcast/{message_id}/view", summary="Increment view count")
def increment_view_count(
    message_id: str,
    svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
):
    count = svc.increment_view_count(message_id)
    return success_response({"view_count": count})


@router.websocket("/v1/ws/masjid/{masjid_id}")
async def masjid_websocket(
    websocket: WebSocket,
    masjid_id: str,
    token: str = Query(...),
):
    app = websocket.app
    user_store = app.state.user_store
    user = user_store.get_user_by_session(token)
    if not user:
        await websocket.close(code=4001)
        return

    conn_mgr: ConnectionManager = app.state.connection_manager
    broadcast_svc: BroadcastFeedService = app.state.broadcast_feed_service
    masjid_svc: MasjidEntityService = app.state.masjid_entity_service

    await conn_mgr.connect(masjid_id, user["user_id"], websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            payload = data.get("payload", {})

            if msg_type == "connect":
                since_str = payload.get("last_message_at")
                since = datetime.fromisoformat(since_str) if since_str else None
                feed = broadcast_svc.get_feed(masjid_id, cursor=None, since=since, limit=50, user_id=user["user_id"])
                await websocket.send_json({"type": "connect_ack", "payload": feed})

            elif msg_type == "post_message":
                masjid_result = masjid_svc.get_masjid(masjid_id)
                masjid_data = masjid_result.get("masjid", {})
                committee = masjid_data.get("management", {}).get("committee", [])
                sender_info = None
                for m in committee:
                    if m.get("user_id") == user["user_id"]:
                        sender_info = {"user_id": m["user_id"], "name": m.get("name", ""), "role": m.get("role", "")}
                        break
                if not sender_info:
                    await websocket.send_json({"type": "error", "payload": {"message": "Only committee members can post"}})
                    continue

                message = broadcast_svc.post_message(masjid_id, sender_info, payload)
                await conn_mgr.broadcast_to_masjid(masjid_id, {"type": "new_message", "payload": message})

            elif msg_type == "react":
                result = broadcast_svc.toggle_reaction(payload["message_id"], user["user_id"], payload["emoji"])
                await conn_mgr.broadcast_to_masjid(masjid_id, {
                    "type": "reaction_update",
                    "payload": {
                        "message_id": payload["message_id"],
                        "reaction_counts": result.get("reaction_counts", result),
                    },
                })

            elif msg_type == "delete_message":
                broadcast_svc.delete_message(payload["message_id"], user["user_id"])
                await conn_mgr.broadcast_to_masjid(masjid_id, {
                    "type": "message_deleted",
                    "payload": {"message_id": payload["message_id"]},
                })

    except WebSocketDisconnect:
        await conn_mgr.disconnect(masjid_id, user["user_id"])
