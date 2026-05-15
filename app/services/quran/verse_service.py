from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.enums.api_endpoints import ApiEndpoint
from app.services.quran.base_service import BaseQuranService


def _verse_params(
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
) -> Dict[str, str]:
    params: Dict[str, str] = {
        "language": language,
        "translation_fields": "language_name",
        "fields": "text_uthmani",
    }
    if translations:
        params["translations"] = ",".join(map(str, translations))
    if words:
        params["words"] = "true"
    if page is not None:
        params["page"] = str(page)
    if per_page is not None:
        params["per_page"] = str(per_page)
    return params


class VerseService(BaseQuranService):
    def by_chapter(self, chapter_id: int, **kwargs: Any) -> Any:
        return self._get(
            f"{ApiEndpoint.CONTENT_API_V4.value}/verses/by_chapter/{chapter_id}",
            _verse_params(**kwargs),
        )

    def by_juz(self, juz_id: int, **kwargs: Any) -> Any:
        return self._get(
            f"{ApiEndpoint.CONTENT_API_V4.value}/verses/by_juz/{juz_id}",
            _verse_params(**kwargs),
        )
