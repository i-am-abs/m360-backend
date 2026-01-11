from services.base_service import BaseService


class RubElHizbService(BaseService):

    def get_rub_el_hizbs(self, language: str = "en"):
        return self._get("/content/api/v4/rub_el_hizbs", {"language": language})

    def get_rub_el_hizb(self, rub_el_hizb_id: int, language: str = "en"):
        return self._get(
            f"/content/api/v4/rub_el_hizbs/{rub_el_hizb_id}", {"language": language}
        )