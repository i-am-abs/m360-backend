from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class FeatureContext:
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    headers: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def get_header(self, name: str) -> Optional[str]:
        name_lower = name.lower()
        for k, v in self.headers.items():
            if k.lower() == name_lower:
                return v
        return None
