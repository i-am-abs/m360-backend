from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.enums.masjid_amenity import Amenity
from app.core.enums.prayer import PrayerName


class PrayerTimingItem(BaseModel):
    prayer: str
    adhan: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    iqamah: str = Field(..., pattern=r"^\d{2}:\d{2}$")

    @field_validator("prayer")
    @classmethod
    def valid_prayer(cls, value: str) -> str:
        if value not in PrayerName.values():
            raise ValueError(f"prayer must be one of: {', '.join(PrayerName.values())}")
        return value


class MasjidTimingsRequest(BaseModel):
    timings: list[PrayerTimingItem] = Field(..., min_length=1, max_length=5)


class MasjidAmenitiesRequest(BaseModel):
    amenities: list[str] = Field(..., min_length=0)

    @field_validator("amenities")
    @classmethod
    def valid_amenities(cls, values: list[str]) -> list[str]:
        allowed = set(Amenity.values())
        invalid = [v for v in values if v not in allowed]
        if invalid:
            raise ValueError(f"invalid amenities: {', '.join(invalid)}")
        return list(dict.fromkeys(values))


class AdminStatusView(BaseModel):
    label: str
    message: str = ""


class MasjidListItem(BaseModel):
    id: str
    name: str
    admin_status: AdminStatusView = Field(serialization_alias="adminStatus")

    model_config = {"populate_by_name": True}


class MasjidTimingsResponse(BaseModel):
    place_id: str = Field(serialization_alias="placeId")
    timings: list[PrayerTimingItem]

    model_config = {"populate_by_name": True}
