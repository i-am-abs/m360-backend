from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AuditLogRepository(ABC):
    @abstractmethod
    def write(self, entry: Dict[str, Any]) -> None:
        """Persist an audit log entry."""

    @abstractmethod
    def list_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch audit history for a resource."""
