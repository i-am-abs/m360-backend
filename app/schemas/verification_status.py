from __future__ import annotations

from pydantic import BaseModel

from app.core.enums.verification_status import VerificationStatus


class VerificationStatusUpdate(BaseModel):
    status: VerificationStatus
