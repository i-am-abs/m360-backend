from typing import Any

from services.base_service import BaseService


class ChapterService(BaseService):
    def get_chapters(self, language: str = "en") -> Any:
        return self._get("/v4/chapters", params={"language": language})

    def get_chapter(self, chapter_id: int, language: str = "en") -> Any:
        return self._get(f"/v4/chapters/{chapter_id}", params={"language": language})
