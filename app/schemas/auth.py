from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


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
    retry_channel: Optional[Literal["sms", "voice", "whatsapp", "email"]] = None


class OtpVerifyRequest(BaseModel):
    phone_number: str
    req_id: str
    otp: str
