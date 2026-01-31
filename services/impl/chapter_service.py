from services.base_service import BaseService

class ChapterService(BaseService):

    def get_chapters(self, language="en"):
        data = self._get("/content/api/v4/chapters", {"language": language})
        if language and language not in ("en", "ar"):
            chapters = data.get("chapters") if isinstance(data, dict) else None
            if chapters and isinstance(chapters, list):
                for ch in chapters:
                    t = ch.get("translated_name") if isinstance(ch, dict) else None
                    if t and isinstance(t, dict) and t.get("name"):
                        t["language_name"] = {
                            "hi": "hindi",
                            "en": "english",
                            "ar": "arabic",
                        }.get(language, language)
        return data

    def get_chapter(self, chapter_id, language="en"):
        data = self._get(
            f"/content/api/v4/chapters/{chapter_id}", {"language": language}
        )
        # if getattr(self.config, "use_local_chapter_translations", True):
        #     data = localize_chapters(data, language)
        if language and language not in ("en", "ar") and isinstance(data, dict):
            ch = data.get("chapter")
            if ch and isinstance(ch, dict):
                t = ch.get("translated_name")
                if t and isinstance(t, dict) and t.get("name"):
                    # t["name"] = translate_text(t.get("name"), target_language=language)
                    t["language_name"] = {
                        "hi": "hindi",
                        "en": "english",
                        "ar": "arabic",
                    }.get(language, language)
        return data
