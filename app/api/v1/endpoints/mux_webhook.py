from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from app.services.broadcast_feed_service import BroadcastFeedService
from app.services.mux_service import MuxService
from app.utils.response import success_response
from app.api.deps import get_broadcast_feed_service

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/mux", summary="Mux webhook")
async def mux_webhook(
    request: Request,
    webhook_signature: str = Header(..., alias="Mux-Signature"),
    broadcast_svc: BroadcastFeedService = Depends(get_broadcast_feed_service),
):
    body = await request.body()
    mux = MuxService()
    payload = mux.verify_webhook(body, webhook_signature)
    if not payload:
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "invalid_signature"}, status_code=400)

    event_type = payload.get("type", "")
    data = payload.get("data", {})

    if event_type in ("video.asset.ready", "video.asset.created"):
        asset_id = data.get("id")
        playback_id = None
        playbacks = data.get("playback_ids") or []
        for pb in playbacks:
            if pb.get("policy") == "public":
                playback_id = pb.get("id")
                break

        if asset_id and playback_id:
            upload_id = data.get("upload_id")
            broadcast_svc.handle_mux_asset_ready(
                asset_id=asset_id,
                playback_id=playback_id,
                upload_id=upload_id,
            )

    return success_response({"received": True})
