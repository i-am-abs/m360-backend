"""
Verse service - fetches verses by chapter or juz from Quran API.
"""
from typing import Any, List, Optional

from services.base_service import BaseService


class VerseService(BaseService):

    def by_chapter(
        self,
        chapter_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Any:
        params: dict = {"language": language, "words": words}
        if translations:
            params["translations"] = ",".join(str(t) for t in translations)
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self._get(f"/v4/verses/by-chapter/{chapter_id}", params=params)

    def by_juz(
        self,
        juz_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Any:
        params: dict = {"language": language, "words": words}
        if translations:
            params["translations"] = ",".join(str(t) for t in translations)
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self._get(f"/v4/verses/by-juz/{juz_id}", params=params)
