from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.enums.broadcast import BroadcastMessageType


class BroadcastCreateRequest(BaseModel):
    caption: str = Field(..., min_length=1, max_length=2000)
    video_uri: Optional[str] = Field(None, alias="videoUri", max_length=2048)
    thumbnail_uri: Optional[str] = Field(None, alias="thumbnailUri", max_length=2048)
    message_type: str = Field(default=BroadcastMessageType.TEXT.value, alias="messageType")

    model_config = {"populate_by_name": True}

    @field_validator("message_type")
    @classmethod
    def valid_message_type(cls, value: str) -> str:
        if value not in BroadcastMessageType.values():
            raise ValueError(
                f"messageType must be one of: {', '.join(BroadcastMessageType.values())}"
            )
        return value


class BroadcastItem(BaseModel):
    id: str
    masjid_id: str = Field(serialization_alias="masjidId")
    caption: str
    video_uri: Optional[str] = Field(None, serialization_alias="videoUri")
    thumbnail_uri: Optional[str] = Field(None, serialization_alias="thumbnailUri")
    message_type: str = Field(serialization_alias="messageType")
    seq: int
    created_at: str = Field(serialization_alias="createdAt")
    created_by: Optional[str] = Field(None, serialization_alias="createdBy")

    model_config = {"populate_by_name": True}


class BroadcastPage(BaseModel):
    items: List[BroadcastItem]
    next_cursor: Optional[int] = Field(None, serialization_alias="nextCursor")
    has_more: bool = Field(serialization_alias="hasMore")

    model_config = {"populate_by_name": True}


class BroadcastDeliveryResult(BaseModel):
    broadcast_id: str = Field(serialization_alias="broadcastId")
    recipients: int
    sent: int
    failed: int

    model_config = {"populate_by_name": True}
