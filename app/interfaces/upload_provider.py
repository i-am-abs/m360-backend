from __future__ import annotations

from abc import ABC, abstractmethod


class UploadProvider(ABC):
    @abstractmethod
    def upload(
            self,
            file_bytes: bytes,
            filename: str,
            content_type: str,
    ) -> str:
        pass

    @abstractmethod
    def supports(self, content_type: str) -> bool:
        pass
