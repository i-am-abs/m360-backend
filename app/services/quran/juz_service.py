from __future__ import annotations

from typing import Any

from app.services.quran.base_service import BaseQuranService


class JuzService(BaseQuranService):
    def get_juzs(self, language: str = "en") -> Any:
        return self._get(
            "/content/api/v4/juzs",
            {"language": language},
        )
