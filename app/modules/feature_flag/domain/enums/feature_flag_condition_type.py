from enum import Enum


class FeatureFlagConditionType(str, Enum):
    LOCATION = "LOCATION"
    USER = "USER"
    ENVIRONMENT = "ENVIRONMENT"
    REGION = "REGION"
    PERCENTAGE_ROLLOUT = "PERCENTAGE_ROLLOUT"
    TIME_BASED = "TIME_BASED"
    COMPOSITE = "COMPOSITE"
