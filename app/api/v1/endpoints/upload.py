from __future__ import annotations

from fastapi import APIRouter

from app.services.mux_service import MuxService
from app.utils.response import success_response

router = APIRouter(tags=["upload"])


@router.get("/upload/mux-url", summary="Get Mux direct upload URL")
def get_mux_upload_url():
    mux = MuxService()
    result = mux.create_direct_upload()
    return success_response(result)
