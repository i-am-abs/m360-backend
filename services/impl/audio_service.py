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
        return self._get(
            f"/v4/recitations/{recitation_id}/by-ayah/{verse_key}",
        )
