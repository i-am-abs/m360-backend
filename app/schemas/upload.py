from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    url: str


class UploadMetadata(BaseModel):
    filename: str
    content_type: str
    size_bytes: int = Field(..., ge=1)
