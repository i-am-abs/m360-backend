from typing import Any

from services.base_service import BaseService


class AudioService(BaseService):
    def get_chapter_recitation_audio(
        self,
        chapter_id: int,
        recitation_id: int,
        segments: bool = False,
    ) -> Any:
        params: dict = {}
        if segments:
            params["segments"] = "true"
        return self._get(
            f"/v4/recitations/{recitation_id}/by-chapter/{chapter_id}",
            params=params if params else None,
        )

    def get_verse_recitation_audio(
        self,
        verse_key: str,
        recitation_id: int,
    ) -> Any:
    def get_verse_recitation_audio(self,  recitation_id: int, verse_key: Optional[str] = None, chapter_number : Optional[int] = None, juz_number: Optional[int] = None):
        params = {}

        if verse_key:
            params["verse_key"] = verse_key

        if chapter_number:
            params["chapter_number"] = chapter_number

        if juz_number:
            params["juz_number"] = juz_number

        return self._get(
            f"/v4/recitations/{recitation_id}/by-ayah/{verse_key}",
            f"/content/api/v4/quran/recitations/{recitation_id}", params
        )
