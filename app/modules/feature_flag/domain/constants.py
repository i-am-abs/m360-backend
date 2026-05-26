from __future__ import annotations

from typing import Any, Optional

ALLOWED_FEATURE_FLAG_CONDITION_TYPES: frozenset[str] = frozenset(
    {
        "LOCATION",
        "USER",
        "ENVIRONMENT",
        "REGION",
        "PERCENTAGE_ROLLOUT",
        "TIME_BASED",
        "COMPOSITE",
    }
)

ALLOWED_FEATURE_FLAG_STATUSES: frozenset[str] = frozenset({"ACTIVE", "INACTIVE"})

DEFAULT_FEATURE_FLAG_STATUS: str = "ACTIVE"


def normalizeFeatureFlagConditionType(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("condition_type must be a string")
    normalizedConditionType = value.strip().upper()
    if normalizedConditionType not in ALLOWED_FEATURE_FLAG_CONDITION_TYPES:
        allowedConditionTypes = ", ".join(sorted(ALLOWED_FEATURE_FLAG_CONDITION_TYPES))
        raise ValueError(f"condition_type must be one of: {allowedConditionTypes}")
    return normalizedConditionType


def normalizeOptionalFeatureFlagConditionType(value: Any) -> Optional[str]:
    if value is None:
        return None
    return normalizeFeatureFlagConditionType(value)


def normalizeFeatureFlagStatus(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("feature_flag_status must be a string")
    normalizedFeatureFlagStatus = value.strip().upper()
    if normalizedFeatureFlagStatus not in ALLOWED_FEATURE_FLAG_STATUSES:
        allowedFeatureFlagStatuses = ", ".join(sorted(ALLOWED_FEATURE_FLAG_STATUSES))
        raise ValueError(f"feature_flag_status must be one of: {allowedFeatureFlagStatuses}")
    return normalizedFeatureFlagStatus


def normalizeOptionalFeatureFlagStatus(value: Any) -> Optional[str]:
    if value is None:
        return None
    return normalizeFeatureFlagStatus(value)
