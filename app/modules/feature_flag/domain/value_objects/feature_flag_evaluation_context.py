from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


class FeatureFlagEvaluationContext:
    def __init__(
            self,
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
            userId: Optional[str] = None,
            environmentName: Optional[str] = None,
            regionCode: Optional[str] = None,
            evaluationTimestamp: Optional[datetime] = None,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.userId = userId
        self.environmentName = environmentName
        self.regionCode = regionCode
        self.evaluationTimestamp = evaluationTimestamp or datetime.now(timezone.utc)
