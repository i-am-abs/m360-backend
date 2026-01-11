from typing import Optional
from services.base_service import BaseService


class ManzilService(BaseService):

    def get_manzils(self, language: str = "en"):
        return self._get("/content/api/v4/manzils", {"language": language})

    def get_manzil(self, manzil_id: int, language: str = "en"):
        return self._get(f"/content/api/v4/manzils/{manzil_id}", {"language": language})