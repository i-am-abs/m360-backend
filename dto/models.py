from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str


class TokenRequest(BaseModel):
    force_refresh: bool = False
