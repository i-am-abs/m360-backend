from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FeatureFlagsResponse(BaseModel):
    verification: bool = False
    timings: bool = False
    committee_registration: bool = False


class FeatureLocationQuery(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_key: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
