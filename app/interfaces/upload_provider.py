from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class UploadProvider(ABC):
    @abstractmethod
    def upload(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload file and return public URL."""

    @abstractmethod
    def supports(self, content_type: str) -> bool:
        """Return True when this provider handles the content type."""
