from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.feature_flag.domain.enums.feature_flag_condition_type import FeatureFlagConditionType
from app.modules.feature_flag.domain.enums.feature_flag_status import FeatureFlagStatus


class GeofenceRegionRequestDto(BaseModel):
    center_latitude: float = Field(..., ge=-90.0, le=90.0)
    center_longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_in_meters: float = Field(..., gt=0.0)


class FeatureFlagCreateRequestDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_name: str = Field(..., min_length=1, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default="", max_length=1024)
    globally_enabled: bool = True
    default_enabled: bool = False
    condition_type: FeatureFlagConditionType
    condition_configuration: Dict[str, Any] = Field(default_factory=dict)
    feature_flag_status: FeatureFlagStatus = FeatureFlagStatus.ACTIVE

    @field_validator("feature_name")
    @classmethod
    def normalizeFeatureName(cls, value: str) -> str:
        normalizedName = value.strip().upper()
        if not normalizedName:
            raise ValueError("feature_name must not be blank")
        return normalizedName


class FeatureFlagUpdateRequestDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=1024)
    globally_enabled: Optional[bool] = None
    default_enabled: Optional[bool] = None
    condition_type: Optional[FeatureFlagConditionType] = None
    condition_configuration: Optional[Dict[str, Any]] = None
    feature_flag_status: Optional[FeatureFlagStatus] = None


class FeatureFlagEvaluationRequestDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_name: str = Field(..., min_length=1, max_length=128)
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    user_id: Optional[str] = Field(default=None, max_length=128)
    environment_name: Optional[str] = Field(default=None, max_length=64)
    region_code: Optional[str] = Field(default=None, max_length=16)

    @field_validator("feature_name")
    @classmethod
    def normalizeFeatureName(cls, value: str) -> str:
        return value.strip().upper()


class FeatureFlagResponseDto(BaseModel):
    feature_flag_id: str
    feature_name: str
    display_name: str
    description: str
    globally_enabled: bool
    default_enabled: bool
    condition_type: FeatureFlagConditionType
    condition_configuration: Dict[str, Any]
    feature_flag_status: FeatureFlagStatus
    created_at: str
    updated_at: str


class FeatureFlagEvaluationResponseDto(BaseModel):
    feature_name: str
    enabled: bool
    reason: str


class FeatureFlagListResponseDto(BaseModel):
    count: int
    feature_flags: List[FeatureFlagResponseDto]
