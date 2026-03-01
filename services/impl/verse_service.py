from typing import Optional

from constants.api_endpoints import ApiEndpoints
from services.base_service import BaseService


def _verse_params(
    language: str = "en",
    translations: Optional[list] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
) -> dict:
    params = {
        "language": language,
        "translation_fields": "language_name",
        "fields": "text_uthmani",
    }
    if translations:
        params["translations"] = ",".join(map(str, translations))
    if words:
        params["words"] = "true"
    if page is not None:
        params["page"] = page
    if per_page is not None:
        params["per_page"] = per_page
    return params


class VerseService(BaseService):

    def by_chapter(
        self,
        chapter_id: int,
        language: str = "en",
        translations: Optional[list] = None,
        words: bool = False,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ):
        params = _verse_params(language, translations, words, page, per_page)
        return self._get(
            f"{ApiEndpoints.CONTENT_API_V4.value}/verses/by_chapter/{chapter_id}", params
        )

    def by_juz(
        self,
        juz_id: int,
        language: str = "en",
        translations: Optional[list] = None,
        words: bool = False,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ):
        params = _verse_params(language, translations, words, page, per_page)
        return self._get(
            f"{ApiEndpoints.CONTENT_API_V4.value}/verses/by_juz/{juz_id}", params
        )
