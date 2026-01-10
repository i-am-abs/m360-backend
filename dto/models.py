from pydantic import BaseModel
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str


class TokenRequest(BaseModel):
    force_refresh: bool = False


class DeviceRegisterRequest(BaseModel):
    uuid: Optional[str] = None
