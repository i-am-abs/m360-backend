from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.core.enums.api_endpoints import ApiEndpoint
from app.modules.feature_flag.api.controllers.feature_flag_controller import FeatureFlagController
from app.modules.feature_flag.application.dto.feature_flag_dto import (
    FeatureFlagCreateRequestDto,
    FeatureFlagEvaluationRequestDto,
    FeatureFlagUpdateRequestDto,
)
from app.utils.response import success_response

router = APIRouter(tags=["feature-flags"])


def get_feature_flag_controller(request: Request) -> FeatureFlagController:
    return FeatureFlagController(
        featureFlagManagementService=request.app.state.feature_flag_management_service,
    )


@router.get(ApiEndpoint.FEATURE_FLAGS.value, summary="List all feature flags")
def list_feature_flags(
        controller: FeatureFlagController = Depends(get_feature_flag_controller),
):
    return success_response(controller.listAllFeatureFlags())


@router.get(ApiEndpoint.FEATURE_FLAG_BY_NAME.value, summary="Get feature flag by name")
def get_feature_flag_by_name(
        feature_name: str,
        controller: FeatureFlagController = Depends(get_feature_flag_controller),
):
    return success_response(controller.getFeatureFlagByName(feature_name))


@router.post(ApiEndpoint.FEATURE_FLAGS.value, summary="Create feature flag")
def create_feature_flag(
        createRequest: FeatureFlagCreateRequestDto,
        controller: FeatureFlagController = Depends(get_feature_flag_controller),
):
    return success_response(
        controller.createFeatureFlag(createRequest),
        message="Feature flag created",
    )


@router.put(ApiEndpoint.FEATURE_FLAG_BY_NAME.value, summary="Update feature flag")
def update_feature_flag(
        feature_name: str,
        updateRequest: FeatureFlagUpdateRequestDto,
        controller: FeatureFlagController = Depends(get_feature_flag_controller),
):
    return success_response(
        controller.updateFeatureFlag(feature_name, updateRequest),
        message="Feature flag updated",
    )


@router.delete(ApiEndpoint.FEATURE_FLAG_BY_NAME.value, summary="Delete feature flag")
def delete_feature_flag(
        feature_name: str,
        controller: FeatureFlagController = Depends(get_feature_flag_controller),
):
    return success_response(
        controller.deleteFeatureFlag(feature_name),
        message="Feature flag deleted",
    )


@router.post(ApiEndpoint.FEATURE_FLAG_EVALUATE.value, summary="Evaluate feature flag")
def evaluate_feature_flag(
        evaluationRequest: FeatureFlagEvaluationRequestDto,
        controller: FeatureFlagController = Depends(get_feature_flag_controller),
):
    return success_response(controller.evaluateFeatureFlag(evaluationRequest))


@router.get(ApiEndpoint.FEATURE_FLAG_EVALUATE_BY_NAME.value, summary="Evaluate feature flag (query)")
def evaluate_feature_flag_by_query(
        feature_name: str,
        latitude: Optional[float] = Query(default=None, ge=-90.0, le=90.0),
        longitude: Optional[float] = Query(default=None, ge=-180.0, le=180.0),
        user_id: Optional[str] = Query(default=None),
        environment_name: Optional[str] = Query(default=None),
        region_code: Optional[str] = Query(default=None),
        controller: FeatureFlagController = Depends(get_feature_flag_controller),
):
    return success_response(
        controller.evaluateFeatureFlagByQueryParameters(
            featureName=feature_name,
            latitude=latitude,
            longitude=longitude,
            userId=user_id,
            environmentName=environment_name,
            regionCode=region_code,
        )
    )
