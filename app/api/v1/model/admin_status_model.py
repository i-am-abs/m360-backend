from typing import Optional
from app.core.enums.admin_status import AdminRegistrationStatus
from pydantic import BaseModel, Field

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