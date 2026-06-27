from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.enums.role import UserRole


class VerificationRequestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    profile_image: Optional[str] = Field(None, alias="profileImage")
    phone: str = Field(..., min_length=10, max_length=15)
    role: str = Field(..., min_length=1, max_length=50)

    model_config = {"populate_by_name": True}

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        allowed = {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}
        if value not in allowed:
            raise ValueError(f"role must be one of: {', '.join(sorted(allowed))}")
        return value


class VerificationRequestResponse(BaseModel):
    id: str
    name: str
    profile_image: Optional[str] = Field(None, serialization_alias="profileImage")
    phone: str
    role: str
    status: str

    model_config = {"populate_by_name": True}


class RoleItem(BaseModel):
    id: str
    label: str


class RolesResponse(BaseModel):
    roles: list[RoleItem]
