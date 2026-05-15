from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.core.enums.msg91 import RetryChannel


class TokenRequest(BaseModel):
    force_refresh: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str


class PhoneLoginRequest(BaseModel):
    phone_number: str


class OtpRetryRequest(BaseModel):
    phone_number: str
    req_id: str
    retry_channel: Optional[RetryChannel] = None


class OtpVerifyRequest(BaseModel):
    phone_number: str
    req_id: str
    otp: str
