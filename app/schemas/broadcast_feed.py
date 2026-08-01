from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class BroadcastMessageCreate(BaseModel):
    message_type: str = "text"
    text: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    mux_asset_id: Optional[str] = None
    mux_upload_id: Optional[str] = None
    campaign_id: Optional[str] = None


class CampaignCardCreate(BaseModel):
    campaign_id: str
    text: Optional[str] = None


class ReactionToggle(BaseModel):
    emoji: str
