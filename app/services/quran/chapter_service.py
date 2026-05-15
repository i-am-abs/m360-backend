from __future__ import annotations

from typing import Any

from app.core.enums.api_endpoints import ApiEndpoint
from app.services.quran.base_service import BaseQuranService


class ChapterService(BaseQuranService):
    def get_chapters(self, language: str = "en") -> Any:
        return self._get(
            f"{ApiEndpoint.CONTENT_API_V4.value}/chapters",
            {"language": language},
        )
