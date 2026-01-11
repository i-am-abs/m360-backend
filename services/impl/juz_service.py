from typing import Optional
from services.base_service import BaseService


class JuzService(BaseService):

    def get_juzs(self, language: str = "en"):
        return self._get("/content/api/v4/juzs", {"language": language})

    def get_juz(self, juz_id: int, language: str = "en"):
        return self._get(f"/content/api/v4/juzs/{juz_id}", {"language": language})