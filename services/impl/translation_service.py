from typing import Optional
from services.base_service import BaseService


class TranslationService(BaseService):

    def get_translations(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/translations", params)

    def get_translation(self, translation_id: int):
        return self._get(f"/content/api/v4/resources/translations/{translation_id}")

    def get_chapter_translation(
        self, chapter_id: int, translation_id: int, language: str = "en"
    ):
        params = {"language": language}
        return self._get(
            f"/content/api/v4/chapter_translations/{translation_id}/{chapter_id}", params
        )

    def get_verse_translation(
        self, verse_key: str, translation_id: int, language: str = "en"
    ):
        params = {"language": language}
        return self._get(
            f"/content/api/v4/verse_translations/{translation_id}/{verse_key}", params
        )