from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.enums.broadcast import DevicePlatform


class FcmTokenRegisterRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=4096)
    platform: Optional[str] = None

    @field_validator("platform")
    @classmethod
    def valid_platform(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if value not in DevicePlatform.values():
            raise ValueError(f"platform must be one of: {', '.join(DevicePlatform.values())}")
        return value


class FcmTokenResponse(BaseModel):
    user_id: str = Field(serialization_alias="userId")
    token_registered: bool = Field(serialization_alias="tokenRegistered")

    model_config = {"populate_by_name": True}


class MasjidFollowResponse(BaseModel):
    masjid_id: str = Field(serialization_alias="masjidId")
    following: bool

    model_config = {"populate_by_name": True}
