from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.role import UserRole


class AdminRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=10, max_length=15)
    profile_image: Optional[str] = Field(None, alias="profileImage")
    role: UserRole = UserRole.ADMIN
    committee_id: Optional[str] = Field(None, alias="committeeId")
    masjid_place_id: Optional[str] = Field(None, alias="masjidPlaceId")

    model_config = {"populate_by_name": True}

    @field_validator("role")
    @classmethod
    def admin_role_only(cls, value: UserRole) -> UserRole:
        if value not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            raise ValueError("Only admin or super_admin roles can be registered via this endpoint")
        return value


class AdminResponse(BaseModel):
    id: str
    name: str
    phone: str
    profile_image: Optional[str] = Field(None, serialization_alias="profileImage")
    role: str
    committee_id: Optional[str] = Field(None, serialization_alias="committeeId")
    masjid_place_id: Optional[str] = Field(None, serialization_alias="masjidPlaceId")
    status: AdminRegistrationStatus

    model_config = {"populate_by_name": True}


class AdminStatusUpdateRequest(BaseModel):
    status: AdminRegistrationStatus
    message: Optional[str] = None
