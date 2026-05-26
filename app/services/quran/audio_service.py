from __future__ import annotations

from typing import Any, Optional

from app.services.quran.base_service import BaseQuranService


class AudioService(BaseQuranService):
    def get_chapter_recitation_audio(self, chapter_id: int, recitation_id: int) -> Any:
        return self._get(f"/content/api/v4/chapter_recitations/{recitation_id}/{chapter_id}")

    def get_verse_recitation_audio(
            self,
            recitation_id: int,
            verse_key: Optional[str] = None,
            chapter_number: Optional[int] = None,
            juz_number: Optional[int] = None,
    ) -> Any:
        params: dict = {}
        if verse_key:
            params["verse_key"] = verse_key
        if chapter_number is not None:
            params["chapter_number"] = chapter_number
        if juz_number is not None:
            params["juz_number"] = juz_number
        return self._get(f"/content/api/v4/quran/recitations/{recitation_id}", params)
