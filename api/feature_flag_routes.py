from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from config.factory.feature_flag_factory import (
    build_context_for_masjid,
    get_feature_flag_provider,
)
from config.feature_flag_config import load_feature_flags_from_file
from constants.api_endpoints import ApiEndpoints
from feature_flags.feature_context import FeatureContext
from logger.Logger import Logger
from utils.http_response import success_response

logger = Logger.get_logger(__name__)
feature_flag_router = APIRouter(tags=["Feature Flags"])


def _build_context(
    request: Request,
    latitude: Optional[float],
    longitude: Optional[float],
    city: Optional[str],
) -> Optional[FeatureContext]:
    if latitude is not None and longitude is not None:
        return build_context_for_masjid(
            latitude=latitude,
            longitude=longitude,
            headers=dict(request.headers),
        )
    if city:
        return FeatureContext(city=city, headers=dict(request.headers))
    return FeatureContext(headers=dict(request.headers))


@feature_flag_router.get(
    ApiEndpoints.FEATURE_FLAGS.value,
    summary="Get all feature flags",
    description=(
        "Returns every configured feature flag with its current enabled/disabled "
        "status. Pass optional latitude, longitude, or city for location-scoped flags."
    ),
)
def get_all_flags(
    request: Request,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None,
):
    try:
        provider = get_feature_flag_provider()
        context = _build_context(request, latitude, longitude, city)
        raw_flags = load_feature_flags_from_file()

        flags = {}
        for flag_name in raw_flags:
            flags[flag_name] = {
                "enabled": provider.is_enabled(flag_name, context),
            }

        return success_response({"flags": flags})
    except Exception as e:
        logger.error("Error fetching feature flags: %s", e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feature flags: {str(e)}",
        )


@feature_flag_router.get(
    ApiEndpoints.FEATURE_FLAG_BY_NAME.value,
    summary="Check a single feature flag",
    description="Returns whether a specific feature flag is enabled for the given context.",
)
def get_flag_by_name(
    flag_name: str,
    request: Request,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None,
):
    raw_flags = load_feature_flags_from_file()
    if flag_name not in raw_flags:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{flag_name}' not found",
        )

    try:
        provider = get_feature_flag_provider()
        context = _build_context(request, latitude, longitude, city)
        enabled = provider.is_enabled(flag_name, context)

        return success_response({
            "flag": flag_name,
            "enabled": enabled,
        })
    except Exception as e:
        logger.error("Error checking flag '%s': %s", flag_name, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check feature flag: {str(e)}",
        )
