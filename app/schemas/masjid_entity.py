from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class FacilitiesUpdate(BaseModel):
    car_parking: Optional[bool] = None
    two_wheeler_parking: Optional[bool] = None
    iftar: Optional[bool] = None
    wuzu_area: Optional[bool] = None
    ac: Optional[bool] = None
    air_coolers: Optional[bool] = None
    male_washroom: Optional[bool] = None
    female_washroom: Optional[bool] = None
    drinking_water: Optional[bool] = None
    wheelchair_accessible: Optional[bool] = None
    mushaf_available: Optional[bool] = None
    chairs: Optional[bool] = None
    janazah_carrier: Optional[bool] = None
    women_prayer_area: Optional[bool] = None
    children_area: Optional[bool] = None
    capacity: Optional[str] = None


class TimingsUpdate(BaseModel):
    fajr: Optional[str] = None
    dhuhr: Optional[str] = None
    asr: Optional[str] = None
    maghrib: Optional[str] = None
    isha: Optional[str] = None
    jummah_first: Optional[str] = None
    jummah_second: Optional[str] = None


class ContactUpdate(BaseModel):
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class SocialLinks(BaseModel):
    facebook: Optional[str] = None
    youtube: Optional[str] = None
    instagram: Optional[str] = None
    telegram: Optional[str] = None


class CommitteeMemberAdd(BaseModel):
    user_id: str
    name: str
    role: str
    phone: Optional[str] = None
    image: Optional[str] = None


class MasjidUpdate(BaseModel):
    name_arabic: Optional[str] = None
    facilities: Optional[FacilitiesUpdate] = None
    services: Optional[Dict[str, bool]] = None
    timings: Optional[TimingsUpdate] = None
    contact: Optional[ContactUpdate] = None
    management: Optional[Dict[str, Any]] = None


class MasjidSyncRequest(BaseModel):
    place_id: str
