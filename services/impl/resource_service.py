from typing import Optional
from services.base_service import BaseService


class ResourceService(BaseService):

    def translations(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/translations", params)

    def tafsirs(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/tafsirs", params)

    def recitations(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/recitations", params)

    def languages(self):
        return self._get("/content/api/v4/resources/languages")

    def chapter_info(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/chapter_info", params)

    def verse_media(self, verse_key: str):
        return self._get(f"/content/api/v4/resources/verse_media/{verse_key}")

    def chapter_reciters(self):
        return self._get("/content/api/v4/resources/chapter_reciters")
