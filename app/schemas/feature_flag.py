from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FeatureFlagsResponse(BaseModel):
    verification: bool = False
    timings: bool = False
    committee_registration: bool = False
    masjid_discovery: bool = False


class FeatureLocationQuery(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_key: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None


class ResolvedLocation(BaseModel):
    """The region a request was matched to, echoed back so clients can debug."""

    location_key: Optional[str] = Field(
        None,
        description="'*' means no launched region matched",
    )
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    matched_by: str = Field(
        ...,
        description="location_key | coordinates | region | default | none",
    )


class ModuleAvailabilityResponse(BaseModel):
    """Whether one module is switched on for the caller's location."""

    module: str = Field(..., description="Module name exactly as requested")
    feature: str = Field(..., description="Canonical feature flag key")
    enabled: bool
    location: ResolvedLocation


class MasjidTabBanners(BaseModel):
    enable_location: bool = Field(
        False,
        serialization_alias="enableLocation",
        description="Show banner to enable device location",
    )
    tap_to_see_nearby: bool = Field(
        False,
        serialization_alias="tapToSeeNearby",
        description="Show banner: tap to see nearby masjids",
    )

    model_config = {"populate_by_name": True}


class MasjidTabLists(BaseModel):
    nearby: bool = False
    followed: bool = False
    admin: bool = False

    model_config = {"populate_by_name": True}


class MasjidTabNearbyMode(BaseModel):
    available: bool = False
    banners: MasjidTabBanners = Field(default_factory=MasjidTabBanners)

    model_config = {"populate_by_name": True}


class MasjidTabResponse(BaseModel):
    """Client contract for the Masjid tab home screen."""

    region_enabled: bool = Field(..., serialization_alias="regionEnabled")
    user_type: str = Field(
        ...,
        serialization_alias="userType",
        description="guest | user | follower | admin",
    )
    primary_screen: str = Field(
        ...,
        serialization_alias="primaryScreen",
        description="nearby | coming_soon | followed_list | admin_followed_list",
    )
    banners: MasjidTabBanners
    lists: MasjidTabLists
    nearby_screen: MasjidTabNearbyMode = Field(
        ...,
        serialization_alias="nearbyScreen",
        description="What to show after user taps 'see nearby'",
    )
    followed_count: int = Field(0, serialization_alias="followedCount")
    admin_count: int = Field(0, serialization_alias="adminCount")

    model_config = {"populate_by_name": True}
