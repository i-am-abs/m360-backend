from typing import Optional
from services.base_service import BaseService


class TafsirService(BaseService):

    def get_tafsirs(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/tafsirs", params)

    def get_tafsir(self, tafsir_id: int):
        return self._get(f"/content/api/v4/resources/tafsirs/{tafsir_id}")

    def get_chapter_tafsir(
        self, chapter_id: int, tafsir_id: int, language: str = "en"
    ):
        params = {"language": language}
        return self._get(
            f"/content/api/v4/chapter_tafsirs/{tafsir_id}/{chapter_id}", params
        )

    def get_verse_tafsir(self, verse_key: str, tafsir_id: int, language: str = "en"):
        params = {"language": language}
        return self._get(
            f"/content/api/v4/verse_tafsirs/{tafsir_id}/{verse_key}", params
        )