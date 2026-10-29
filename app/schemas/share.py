from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ShareChannel = Literal["android_native_share_sheet", "web_native_share_sheet"]
SharePlatform = Literal["android_app", "mobile_web", "desktop_web"]


class ShareCreateRequest(BaseModel):
    message_id: str = Field(min_length=1, max_length=64)
    parent_share_id: Optional[str] = Field(default=None, max_length=64)
    channel: ShareChannel
    platform: SharePlatform
    utm_source: Optional[str] = Field(default=None, max_length=120)
    utm_medium: Optional[str] = Field(default=None, max_length=120)
    utm_campaign: Optional[str] = Field(default=None, max_length=120)
