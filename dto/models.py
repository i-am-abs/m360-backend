from typing import Optional

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str


class TokenRequest(BaseModel):
    force_refresh: bool = False


class PhoneLoginRequest(BaseModel):
    phone_number: str


class OtpRetryRequest(BaseModel):
    phone_number: str
    req_id: str
    retry_channel: Optional[str] = None  # optional: "sms" | "voice" | "whatsapp" | "email"


class OtpVerifyRequest(BaseModel):
    phone_number: str
    req_id: str
    otp: str
