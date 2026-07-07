from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ClaimRequest(BaseModel):
    claimed_role: str
    applicant_note: Optional[str] = None


class ClaimReview(BaseModel):
    reviewer_note: Optional[str] = None