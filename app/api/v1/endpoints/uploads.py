from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user, get_upload_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.services.upload_service import UploadService
from app.utils.response import success_response

router = APIRouter(tags=["uploads"])


@router.post(ApiEndpoint.UPLOADS.value, summary="Upload image or video")
async def upload_file(
        file: UploadFile = File(...),
        current_user: Dict[str, Any] = Depends(get_current_user),
        svc: UploadService = Depends(get_upload_service),
):
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"
    result = svc.upload(content, filename, content_type)
    return success_response(result.model_dump(), message="Upload complete")
