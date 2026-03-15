from typing import Optional

from pydantic import BaseModel


class FeatureFlagQuery(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
