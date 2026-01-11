from typing import Optional
from services.base_service import BaseService


class AudioService(BaseService):

    def get_chapter_recitation_audio(self, chapter_id: int, recitation_id: int):
        return self._get(
            f"/content/api/v4/chapter_recitations/{recitation_id}/{chapter_id}"
        )

    def get_verse_recitation_audio(self, verse_key: str, recitation_id: int):
        return self._get(
            f"/content/api/v4/verse_recitations/{recitation_id}/{verse_key}"
        )

    def get_recitations(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/recitations", params)

    def get_recitation(self, recitation_id: int):
        return self._get(f"/content/api/v4/resources/recitations/{recitation_id}")
