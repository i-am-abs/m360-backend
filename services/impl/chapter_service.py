from constants.api_endpoints import ApiEndpoints
from services.base_service import BaseService


class ChapterService(BaseService):
    def get_chapters(self, language: str = "en"):
        data = self._get(
            f"{ApiEndpoints.CONTENT_API_V4.value}/chapters", {"language": language}
        )
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
