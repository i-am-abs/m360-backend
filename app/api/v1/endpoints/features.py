from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_feature_flag_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.feature_flag import FeatureFlagsResponse
from app.services.feature_flag_service import FeatureFlagService
from app.utils.response import success_response

router = APIRouter(tags=["features"])


@router.get(ApiEndpoint.FEATURES.value, summary="Location-based feature flags")
def get_features(
        latitude: Optional[float] = Query(None),
        longitude: Optional[float] = Query(None),
        location_key: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        city: Optional[str] = Query(None),
        svc: FeatureFlagService = Depends(get_feature_flag_service),
):
    flags = svc.get_features(
        latitude=latitude,
        longitude=longitude,
        location_key=location_key,
        country=country,
        state=state,
        city=city,
    )
    response = FeatureFlagsResponse(**flags)
    return success_response(response.model_dump())
