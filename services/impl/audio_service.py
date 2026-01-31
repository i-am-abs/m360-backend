from typing import Optional
from services.base_service import BaseService


class AudioService(BaseService):

    def get_chapter_recitation_audio(self, chapter_id: int, recitation_id: int):
        return self._get(
            f"/content/api/v4/chapter_recitations/{recitation_id}/{chapter_id}"
        )

    def get_verse_recitation_audio(self,  recitation_id: int, verse_key: Optional[str] = None):
        params = {}

        if verse_key:
            params["verse_key"] = verse_key

        return self._get(
            f"/content/api/v4/quran/recitations/{recitation_id}", params
        )

    def get_juz_recitation_audio(
        self, juz_number: int, recitation_id: int, page: int = 1
    ):
        # Get juz info to find chapters in this juz
        juz_data = self._get(f"/content/api/v4/juzs/{juz_number}")

        # Extract chapter IDs from verse_mapping
        chapter_ids = list(juz_data["juz"]["verse_mapping"].keys())

        # Get chapter recitation audio for each chapter
        audio_files = []
        for chapter_id in chapter_ids:
            try:
                chapter_audio = self._get(
                    f"/content/api/v4/chapter_recitations/{recitation_id}/{chapter_id}"
                )
                audio_files.append(
                    {
                        "chapter_id": int(chapter_id),
                        "audio_file": chapter_audio["audio_file"],
                    }
                )
            except Exception as e:
                # If a chapter audio is not available, skip it
                continue

        return {
            "juz_number": juz_number,
            "recitation_id": recitation_id,
            "audio_files": audio_files,
        }

    def get_recitations(self, language: Optional[str] = None):
        params = {"language": language} if language else {}
        return self._get("/content/api/v4/resources/recitations", params)

    def get_recitation(self, recitation_id: int):
        return self._get(f"/content/api/v4/resources/recitations/{recitation_id}")
