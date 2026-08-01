from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.enums.role import UserRole
from app.utils.admin_link import resolve_system_role_and_designation


class VerificationRequestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    profile_image: Optional[str] = Field(None, alias="profileImage")
    phone: str = Field(..., min_length=10, max_length=15)
    role: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Committee designation (imam, khatib, …) or admin/super_admin",
    )

    model_config = {"populate_by_name": True}

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        try:
            _, designation = resolve_system_role_and_designation(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        # Persist the designation id for committee titles (super_admin stays as-is).
        raw = value.strip().lower().replace(" ", "_")
        if raw == UserRole.SUPER_ADMIN.value:
            return UserRole.SUPER_ADMIN.value
        return designation


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
