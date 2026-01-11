from services.base_service import BaseService


class RukuService(BaseService):

    def get_rukus(self, language: str = "en"):
        return self._get("/content/api/v4/rukus", {"language": language})

    def get_ruku(self, ruku_id: int, language: str = "en"):
        return self._get(f"/content/api/v4/rukus/{ruku_id}", {"language": language})