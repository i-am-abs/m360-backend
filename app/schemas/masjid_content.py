from __future__ import annotations

from typing import Optional

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
        key = (value or "").strip().lower().replace(" ", "_")
        aliases = {
            "zuhr": PrayerName.DHUHR.value,
            "zohr": PrayerName.DHUHR.value,
            "dhuhr": PrayerName.DHUHR.value,
            "asar": PrayerName.ASR.value,
            "magrib": PrayerName.MAGHRIB.value,
            "ishaah": PrayerName.ISHA.value,
        }
        key = aliases.get(key, key)
        if key not in PrayerName.values():
            raise ValueError(f"prayer must be one of: {', '.join(PrayerName.values())}")
        return key


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


class MasjidAnnouncementsEnabledRequest(BaseModel):
    enabled: bool = Field(
        ...,
        description="Set hasAnnouncementsEnabled for this masjid place_id",
    )


class AdminStatusView(BaseModel):
    label: str
    message: str = ""


class MasjidListItem(BaseModel):
    """Legacy minimal list item — listing API now returns full place details dicts."""

    id: str
    name: str
    admin_status: AdminStatusView = Field(serialization_alias="adminStatus")
    address: Optional[str] = None
    location: Optional[dict] = None
    committee: Optional[dict] = None

    model_config = {"populate_by_name": True}


class MasjidTimingsResponse(BaseModel):
    place_id: str = Field(serialization_alias="placeId")
    timings: list[PrayerTimingItem]

    model_config = {"populate_by_name": True}
