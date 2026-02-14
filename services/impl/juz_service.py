from typing import Any

from services.base_service import BaseService


class JuzService(BaseService):
    def get_juzs(self, language: str = "en") -> Any:
        return self._get("/v4/juzs", params={"language": language})

    def get_juz(self, juz_id: int, language: str = "en") -> Any:
        return self._get(f"/v4/juzs/{juz_id}", params={"language": language})
