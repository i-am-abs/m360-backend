from typing import Optional
from services.base_service import BaseService


class HizbService(BaseService):

    def get_hizbs(self, language: str = "en"):
        return self._get("/content/api/v4/hizbs", {"language": language})

    def get_hizb(self, hizb_id: int, language: str = "en"):
        return self._get(f"/content/api/v4/hizbs/{hizb_id}", {"language": language})