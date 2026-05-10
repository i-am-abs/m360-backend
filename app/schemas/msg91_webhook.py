from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Msg91OtpWebhookPayload(BaseModel):
    """Body MSG91 posts for widget OTP events (e.g. SEND_OTP)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event: Optional[str] = None
    request_id: Optional[str] = Field(None, alias="requestId")
    identifier: Optional[str] = None
    widget_id: Optional[str] = Field(None, alias="widgetId")
