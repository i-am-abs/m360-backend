from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    title: str
    description: Optional[str] = None
    target_amount: int
    end_date: datetime


class DonationInitiate(BaseModel):
    amount: int
    payment_method: str
    is_anonymous: bool = False


class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[datetime] = None
