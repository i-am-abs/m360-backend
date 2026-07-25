from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.committee_designation import CommitteeDesignation
from app.core.enums.role import UserRole
from app.utils.admin_link import resolve_system_role_and_designation


class AdminRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=10, max_length=15)
    profile_image: Optional[str] = Field(None, alias="profileImage")
    role: str = Field(
        default=UserRole.ADMIN.value,
        description="System role (admin/super_admin) or committee designation (imam, khatib, …)",
    )
    designation: Optional[str] = Field(
        None,
        description="Committee title; defaults from role when role is a designation",
    )
    committee_id: Optional[str] = Field(None, alias="committeeId")
    masjid_place_id: Optional[str] = Field(None, alias="masjidPlaceId")

    # Resolved after validation — not client-facing required fields
    system_role: str = Field(default=UserRole.ADMIN.value, exclude=True)
    resolved_designation: str = Field(
        default=CommitteeDesignation.ADMIN.value,
        exclude=True,
    )

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def resolve_role_and_designation(self) -> "AdminRegisterRequest":
        try:
            system_role, from_role = resolve_system_role_and_designation(self.role)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        if self.designation:
            designation = CommitteeDesignation.normalize(self.designation)
        else:
            designation = from_role

        self.system_role = system_role
        self.resolved_designation = designation
        return self


class AdminResponse(BaseModel):
    id: str
    name: str
    phone: str
    profile_image: Optional[str] = Field(None, serialization_alias="profileImage")
    role: str
    designation: Optional[str] = None
    designation_label: Optional[str] = Field(
        None,
        serialization_alias="designationLabel",
    )
    committee_id: Optional[str] = Field(None, serialization_alias="committeeId")
    masjid_place_id: Optional[str] = Field(None, serialization_alias="masjidPlaceId")
    status: AdminRegistrationStatus
    onboarding_done: bool = Field(
        False,
        serialization_alias="onboardingDone",
        description="True when prayer timings have been saved for the assigned masjid",
    )

    model_config = {"populate_by_name": True}


class AdminStatusUpdateRequest(BaseModel):
    status: AdminRegistrationStatus
    message: Optional[str] = None
