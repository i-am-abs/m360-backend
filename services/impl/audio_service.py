from typing import Optional

from constants.api_endpoints import ApiEndpoints
from services.base_service import BaseService


class AudioService(BaseService):
    def get_chapter_recitation_audio(self, chapter_id: int, recitation_id: int):
        return self._get(
            f"{ApiEndpoints.CONTENT_API_V4.value}/chapter_recitations/{recitation_id}/{chapter_id}"
        )

    def get_verse_recitation_audio(
        self,
        recitation_id: int,
        verse_key: Optional[str] = None,
        chapter_number: Optional[int] = None,
        juz_number: Optional[int] = None,
    ):
        params = {}
        if verse_key:
            params["verse_key"] = verse_key
        if chapter_number is not None:
            params["chapter_number"] = chapter_number
        if juz_number is not None:
            params["juz_number"] = juz_number
        return self._get(
            f"{ApiEndpoints.CONTENT_API_V4.value}/quran/recitations/{recitation_id}", params
        )
