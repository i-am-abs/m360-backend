from __future__ import annotations

from typing import Any

from app.services.quran.base_service import BaseQuranService


class ChapterService(BaseQuranService):
    def get_chapters(self, language: str = "en") -> Any:
        return self._get(
            "/content/api/v4/chapters",
            {"language": language},
        )
