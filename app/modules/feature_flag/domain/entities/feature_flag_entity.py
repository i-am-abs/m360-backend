from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from app.modules.feature_flag.domain.enums.feature_flag_condition_type import FeatureFlagConditionType
from app.modules.feature_flag.domain.enums.feature_flag_status import FeatureFlagStatus


class FeatureFlagEntity:
    def __init__(
            self,
            featureName: str,
            conditionType: FeatureFlagConditionType,
            conditionConfiguration: Dict[str, Any],
            featureFlagId: Optional[str] = None,
            displayName: Optional[str] = None,
            description: Optional[str] = None,
            globallyEnabled: bool = True,
            defaultEnabled: bool = False,
            featureFlagStatus: FeatureFlagStatus = FeatureFlagStatus.ACTIVE,
            createdAt: Optional[datetime] = None,
            updatedAt: Optional[datetime] = None,
    ) -> None:
        self.featureFlagId = featureFlagId or str(uuid4())
        self.featureName = featureName
        self.displayName = displayName or featureName
        self.description = description or ""
        self.globallyEnabled = globallyEnabled
        self.defaultEnabled = defaultEnabled
        self.conditionType = conditionType
        self.conditionConfiguration = conditionConfiguration
        self.featureFlagStatus = featureFlagStatus
        self.createdAt = createdAt or datetime.now(timezone.utc)
        self.updatedAt = updatedAt or self.createdAt

    def isActive(self) -> bool:
        return self.featureFlagStatus == FeatureFlagStatus.ACTIVE

    def touchUpdatedAt(self) -> None:
        self.updatedAt = datetime.now(timezone.utc)

    def toDictionary(self) -> Dict[str, Any]:
        return {
            "feature_flag_id": self.featureFlagId,
            "feature_name": self.featureName,
            "display_name": self.displayName,
            "description": self.description,
            "globally_enabled": self.globallyEnabled,
            "default_enabled": self.defaultEnabled,
            "condition_type": self.conditionType.value,
            "condition_configuration": self.conditionConfiguration,
            "feature_flag_status": self.featureFlagStatus.value,
            "created_at": self.createdAt.isoformat(),
            "updated_at": self.updatedAt.isoformat(),
        }

    @classmethod
    def fromDictionary(cls, payload: Dict[str, Any]) -> FeatureFlagEntity:
        return cls(
            featureFlagId=str(payload["feature_flag_id"]),
            featureName=str(payload["feature_name"]),
            displayName=str(payload.get("display_name") or payload["feature_name"]),
            description=str(payload.get("description") or ""),
            globallyEnabled=bool(payload.get("globally_enabled", True)),
            defaultEnabled=bool(payload.get("default_enabled", False)),
            conditionType=FeatureFlagConditionType(str(payload["condition_type"])),
            conditionConfiguration=dict(payload.get("condition_configuration") or {}),
            featureFlagStatus=FeatureFlagStatus(
                str(payload.get("feature_flag_status") or FeatureFlagStatus.ACTIVE.value)
            ),
            createdAt=datetime.fromisoformat(str(payload["created_at"])),
            updatedAt=datetime.fromisoformat(str(payload["updated_at"])),
        )
