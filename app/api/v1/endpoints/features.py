from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import (
    get_feature_flag_service,
    get_masjid_tab_service,
    get_optional_current_user,
)
from app.core.enums.api_endpoints import ApiEndpoint
from app.core.enums.error_code import ErrorCode
from app.core.enums.feature_flag import PlatformFeature, module_names
from app.exceptions.base import ApiException
from app.schemas.feature_flag import (
    FeatureFlagsResponse,
    ModuleAvailabilityResponse,
    ResolvedLocation,
)
from app.services.feature_flag_service import FeatureFlagService
from app.services.masjid_tab_service import MasjidTabService
from app.utils.response import success_response

router = APIRouter(tags=["features"])

_LATITUDE = Query(None, ge=-90, le=90, description="WGS84 latitude")
_LONGITUDE = Query(None, ge=-180, le=180, description="WGS84 longitude")


def _location_context(
        latitude: Optional[float],
        longitude: Optional[float],
        location_key: Optional[str],
        country: Optional[str],
        state: Optional[str],
        city: Optional[str],
) -> Dict[str, Any]:
    if (latitude is None) != (longitude is None):
        raise ApiException(
            "latitude and longitude must be supplied together",
            status_code=HTTPStatus.BAD_REQUEST.value,
            code=ErrorCode.BAD_REQUEST,
        )
    return {
        "latitude": latitude,
        "longitude": longitude,
        "location_key": location_key,
        "country": country,
        "state": state,
        "city": city,
    }


@router.get(ApiEndpoint.FEATURES.value, summary="Location-based feature flags")
def get_features(
        latitude: Optional[float] = _LATITUDE,
        longitude: Optional[float] = _LONGITUDE,
        location_key: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        city: Optional[str] = Query(None),
        svc: FeatureFlagService = Depends(get_feature_flag_service),
):
    context = _location_context(
        latitude, longitude, location_key, country, state, city,
    )
    flags = svc.get_features(**context)
    response = FeatureFlagsResponse(**flags)
    return success_response(response.model_dump())


@router.get(
    ApiEndpoint.FEATURE_MODULE.value,
    summary="Is one module enabled at this location?",
)
def get_module_availability(
        module: str = Path(
            ...,
            description="Module name, e.g. 'masjid' or 'masjid_discovery'",
        ),
        latitude: Optional[float] = _LATITUDE,
        longitude: Optional[float] = _LONGITUDE,
        location_key: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        city: Optional[str] = Query(None),
        svc: FeatureFlagService = Depends(get_feature_flag_service),
):
    """Returns `enabled: true` only when the module is switched on for that place."""
    feature = PlatformFeature.parse(module)
    if feature is None:
        raise ApiException(
            f"Unknown module '{module}'. Supported: {', '.join(module_names())}",
            status_code=HTTPStatus.NOT_FOUND.value,
            code=ErrorCode.NOT_FOUND,
        )

    context = _location_context(
        latitude, longitude, location_key, country, state, city,
    )
    resolution = svc.resolve(**context)
    document = resolution.document

    response = ModuleAvailabilityResponse(
        module=module,
        feature=feature.value,
        enabled=resolution.is_enabled(feature),
        location=ResolvedLocation(
            location_key=resolution.location_key,
            country=document.get("country"),
            state=document.get("state"),
            city=document.get("city"),
            matched_by=resolution.matched_by,
        ),
    )
    return success_response(response.model_dump())


@router.get(
    ApiEndpoint.MASJID_TAB.value,
    summary="Masjid tab home UX (region + guest/follower/admin)",
    tags=["masjids"],
)
def get_masjid_tab(
        latitude: Optional[float] = _LATITUDE,
        longitude: Optional[float] = _LONGITUDE,
        location_key: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        city: Optional[str] = Query(None),
        current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
        svc: MasjidTabService = Depends(get_masjid_tab_service),
):
    """
    Returns which Masjid-tab screen/banners/lists the client should show.

    Pass manual or live location via latitude/longitude and/or country/state/city.
    """
    context = _location_context(
        latitude, longitude, location_key, country, state, city,
    )
    result = svc.resolve_tab(current_user=current_user, **context)
    return success_response(result.model_dump(by_alias=True))
